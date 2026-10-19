"""Auditable, local retrieval experiments; never invokes generation."""
import argparse
import hashlib
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from bankscope.evaluation import evaluate
from bankscope.store import Store


def fingerprint(store):
    digest = hashlib.sha256()
    for row in store.db.execute('SELECT doc_id,page,chunk_id,text FROM passages ORDER BY chunk_id'):
        digest.update(json.dumps(list(row), ensure_ascii=False).encode())
        digest.update(b'\n')
    return digest.hexdigest()


class RecordingStore:
    def __init__(self, store):
        self.store = store
        self.trace = []

    def documents(self):
        return self.store.documents()

    def search(self, question, **kwargs):
        start = time.perf_counter()
        hits = self.store.search(question, **kwargs)
        self.trace.append({'seconds': time.perf_counter()-start,
                           'pages': [[h['doc_id'], h['page']] for h in hits],
                           'chunk_ids': [h['chunk_id'] for h in hits]})
        return hits


def run(store, questions, strategies=('bm25',), modes=('document','corpus'), repeats=2, k=5):
    if not 1 <= repeats <= 10:
        raise ValueError('repeats must be between 1 and 10')
    if not strategies or set(strategies)-{'bm25','dense','hybrid','rerank','focused'}:
        raise ValueError('Choose valid retrieval strategies')
    if not modes or set(modes)-{'document','corpus'}:
        raise ValueError('Choose document or corpus modes')
    results=[]
    corpus_sha = fingerprint(store)
    for strategy in strategies:
        for mode in modes:
            runs=[]
            for _ in range(repeats):
                recorder=RecordingStore(store)
                metrics=evaluate(recorder,questions,k,mode,strategy)
                runs.append({'metrics':metrics,'trace':recorder.trace})
            signatures=[[t['chunk_ids'] for t in r['trace']] for r in runs]
            times=[t['seconds'] for r in runs for t in r['trace']]
            results.append({'strategy':strategy,'mode':mode,'runs':runs,
                            'identical_rankings':all(x==signatures[0] for x in signatures) if repeats>1 else None,
                            'median_query_seconds':statistics.median(times) if times else None})
    if fingerprint(store)!=corpus_sha:
        raise ValueError('Corpus changed during experiment; discard this run')
    return {'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),
            'python':platform.python_version(),'paid_calls':0,
            'implementation_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted(Path(__file__).parent.glob('*.py'))},
            'model_configuration':{'embedding':'BAAI/bge-small-en-v1.5',
                                   'reranker':'Xenova/ms-marco-MiniLM-L-6-v2',
                                   'note':'Configured identifiers; model weights are not fingerprinted.'},
            'questions_sha256':hashlib.sha256(Path(questions).read_bytes()).hexdigest(),
            'corpus_passages_sha256':corpus_sha,'documents':store.documents(),
            'k':k,'repeats':repeats,'results':results,
            'limitations':['Page retrieval is not answer accuracy.',
                          'Repeatability is measured on this local index and environment only.',
                          'Timing includes first-query model startup; not a production load test.',
                          'Dataset independence and split quality require separate review.']}


def markdown(result):
    lines=['# Retrieval experiment','',f"Created: {result['created_utc']}",'',
           '| Method | Scope | Queries | Hit@K | MRR | NDCG@K | Median seconds | Same rankings |',
           '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in result['results']:
        m=row['runs'][0]['metrics']
        fmt=lambda x: f'{x:.3f}' if x is not None else 'n/a'
        lines.append(f"| {row['strategy']} | {row['mode']} | {m['evaluated']} | {fmt(m['hit_rate'])} | {fmt(m['mrr'])} | {fmt(m['ndcg'])} | {fmt(row['median_query_seconds'])} | {row['identical_rankings'] if row['identical_rankings'] is not None else 'Not tested'} |")
    lines+=['','Question SHA-256: `'+result['questions_sha256']+'`',
            '','Passage SHA-256: `'+result['corpus_passages_sha256']+'`','']
    lines += ['- '+item for item in result['limitations']]
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/index.sqlite3')
    parser.add_argument('--questions',required=True)
    parser.add_argument('--strategies',nargs='+',default=['bm25'])
    parser.add_argument('--modes',nargs='+',default=['document','corpus'])
    parser.add_argument('--repeats',type=int,default=2)
    parser.add_argument('--k',type=int,default=5)
    parser.add_argument('--output',required=True,help='New output directory; existing runs are never overwritten')
    args=parser.parse_args()
    destination=Path(args.output)
    destination.mkdir(parents=True,exist_ok=False)
    store=Store(args.db)
    try:
        result=run(store,args.questions,args.strategies,args.modes,args.repeats,args.k)
        (destination/'run.json').write_text(json.dumps(result,indent=2)+'\n')
        (destination/'comparison.md').write_text(markdown(result))
        print(markdown(result))
    finally:
        store.close()


if __name__=='__main__':
    main()
