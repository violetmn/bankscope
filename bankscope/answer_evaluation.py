"""Frozen answer-evaluation plans and explicit human scoring; no automatic AI judge."""
import argparse
import hashlib
import json
from pathlib import Path

from bankscope.experiments import fingerprint
from bankscope.generation import generate, GenerationError
from bankscope.store import Store

DIMENSIONS=('correctness','year_and_units','citation_support','completeness','abstention')
RATES={'model':'gpt-4o-mini','input_per_million_usd':0.15,'output_per_million_usd':0.60,
       'checked':'2026-10-19','source':'https://developers.openai.com/api/docs/models/gpt-4o-mini'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preflight(store, questions, strategy='bm25', k=5, limit=20):
    if not 1<=limit<=100 or not 1<=k<=10:
        raise ValueError('Invalid limit or passage count')
    rows=[json.loads(x) for x in Path(questions).read_text().splitlines() if x.strip()]
    if len({q['id'] for q in rows})!=len(rows):
        raise ValueError('Question IDs must be unique')
    indexed={d['id'] for d in store.documents()}
    items=[]
    for q in rows[:limit]:
        if q.get('split')!='development':
            raise ValueError('Pilot preflight accepts development questions only')
        if q.get('doc_name') not in indexed:
            raise ValueError('Every pilot source document must be indexed')
        # Only query and source passages enter the generation plan. Gold answers
        # and expected behavior are deliberately absent.
        hits=store.search(q['question'],k=k,doc_id=q['doc_name'],strategy=strategy)
        if not hits:
            raise ValueError('A pilot item has no retrieved passages; review before paying')
        estimate=len(json.dumps({'question':q['question'],'hits':hits},ensure_ascii=True).encode())+4096
        items.append({'id':q['id'],'question':q['question'],'hits':hits,
                      'conservative_input_tokens':estimate,'maximum_output_tokens':600})
    if not items:raise ValueError('No questions selected')
    estimate=sum(i['conservative_input_tokens']*RATES['input_per_million_usd']/1e6+
                 600*RATES['output_per_million_usd']/1e6 for i in items)
    return {'schema_version':1,'status':'awaiting_budget_approval','paid_calls':0,
            'questions_sha256':sha(questions),'corpus_passages_sha256':fingerprint(store),
            'strategy':strategy,'mode':'document','k':k,'items':items,'pricing':RATES,
            'estimated_upper_cost_usd':round(estimate,6),
            'estimate_note':'Conservative byte-based input estimate plus 4096-token allowance; 600 output tokens per call. Not a provider billing guarantee. No retries.',
            'limitations':['Retrieval + generation pipeline only; structured table routing is not evaluated here.',
                           'Reference answers and labels are not included in the generation plan.']}


def execute(plan_path, output, approved_cap_usd):
    plan=json.loads(Path(plan_path).read_text())
    if approved_cap_usd<=0 or plan['estimated_upper_cost_usd']>approved_cap_usd:
        raise ValueError('Estimated cost exceeds approved run cap')
    if plan['pricing']['model']!='gpt-4o-mini':
        raise ValueError('Plan model differs from generator model')
    destination=Path(output);destination.mkdir(parents=True,exist_ok=False)
    # Immutable plan snapshot; completion artifacts are written after each attempt.
    (destination/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    answers=[]
    for item in plan['items']:
        try:
            result=generate(item['question'],item['hits'],ledger=destination/'usage.sqlite3',audit=True)
        except (GenerationError, ValueError) as exc:
            result={'status':'provider_error','answer':str(exc)}
        row={'id':item['id'],'question':item['question'],'response':result}
        answers.append(row)
        print(f"Answer {len(answers)}/{len(plan['items'])}: {item['id']} — {result.get('status','unknown')}",flush=True)
        with (destination/'answers.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        if result.get('status')=='provider_error':
            break  # Authentication, billing and network failures stop the batch.
    reviews=[{'id':a['id'],'reviewer':'','reference_verified':False,
              **{d:None for d in DIMENSIONS},'notes':''} for a in answers]
    (destination/'reviews.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in reviews))
    (destination/'run.json').write_text(json.dumps({'plan_sha256':sha(plan_path),
        'approved_cap_usd':approved_cap_usd,'attempted_answers':len(answers),
        'planned_answers':len(plan['items']),'complete':len(answers)==len(plan['items']),
        'status':'awaiting_independent_human_review'},indent=2)+'\n')


def score(reviews, expected_ids):
    rows=[json.loads(x) for x in Path(reviews).read_text().splitlines() if x.strip()]
    if len({r['id'] for r in rows})!=len(rows) or {r['id'] for r in rows}!=set(expected_ids):
        raise ValueError('Reviews must match every answer ID exactly once')
    if not rows:raise ValueError('No reviews')
    for row in rows:
        if not row.get('reviewer','').strip() or row.get('reference_verified') is not True:
            raise ValueError('Named reviewer and verified reference required')
        if not row.get('notes','').strip():raise ValueError('Review notes required')
        for d in DIMENSIONS:
            value=row.get(d)
            if value!='n/a' and (type(value) is not int or value not in {0,1,2}):
                raise ValueError('Scores must be 0, 1, 2, or n/a; blanks are not passing scores')
    metrics={}
    for d in DIMENSIONS:
        values=[r[d] for r in rows if r[d]!='n/a']
        metrics[d]={'scored':len(values),'not_applicable':len(rows)-len(values),
                    'mean_out_of_two':sum(values)/len(values) if values else None,
                    'fully_correct':sum(v==2 for v in values)}
    return {'reviewed_answers':len(rows),'dimensions':metrics,
            'method':'Human rubric scores, not an LLM judge or automatic factuality metric.'}


def main():
    from bankscope.config import load_private_env
    load_private_env()
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    pre=sub.add_parser('preflight');pre.add_argument('--db',required=True);pre.add_argument('--questions',required=True)
    pre.add_argument('--output',required=True);pre.add_argument('--strategy',default='bm25',choices=['bm25','dense','hybrid','rerank','focused'])
    pre.add_argument('--limit',type=int,default=20)
    ex=sub.add_parser('execute');ex.add_argument('--plan',required=True);ex.add_argument('--output',required=True)
    ex.add_argument('--approved-cap-usd',type=float,required=True)
    sc=sub.add_parser('score');sc.add_argument('--reviews',required=True);sc.add_argument('--answers',required=True)
    a=p.parse_args()
    if a.command=='preflight':
        store=Store(a.db)
        try:result=preflight(store,a.questions,a.strategy,limit=a.limit)
        finally:store.close()
        with open(a.output,'x') as f:f.write(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='items'},indent=2))
    elif a.command=='execute':execute(a.plan,a.output,a.approved_cap_usd)
    else:
        ids=[json.loads(x)['id'] for x in Path(a.answers).read_text().splitlines() if x.strip()]
        print(json.dumps(score(a.reviews,ids),indent=2))


if __name__=='__main__':main()
