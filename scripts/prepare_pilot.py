"""Build a 20-item banking development pilot from public labels and synthetic controls."""
import json
from pathlib import Path
from bankscope.store import Store


def main():
    root=Path('data/benchmarks/pilot-v1');root.mkdir(parents=True,exist_ok=True)
    questions=[json.loads(x) for x in Path('data/financebench/financebench_open_source.jsonl').read_text().splitlines()]
    questions=[q for q in questions if q['company'] in {'American Express','JPMorgan'}]
    store=Store(root/'index.sqlite3')
    metadata=[json.loads(x) for x in Path('data/financebench/financebench_document_information.jsonl').read_text().splitlines()]
    metadata={d['doc_name']:d for d in metadata}
    try:
        for name in sorted({q['doc_name'] for q in questions}):
            d=metadata[name];year=int(name.split('_')[1][:4])
            path=Path('data/financebench/pdfs')/(name+'.pdf')
            url='https://raw.githubusercontent.com/patronus-ai/financebench/main/pdfs/'+name+'.pdf'
            if name not in {x['id'] for x in store.documents()}:
                store.ingest_pdf(path,name,d['company'],year,url,'pdfium')
                print('Indexed',name,flush=True)
        result=[]
        for q in questions:
            result.append({**q,'id':q['financebench_id'],'split':'development',
                           'reference_review':'upstream_annotation_pending_independent_check',
                           'expected_behavior':'answer_from_evidence',
                           'source':'FinanceBench public release; not a new held-out sample'})
        negatives=[
          ('What were American Express customer deposits in fiscal year 2035?','AMERICANEXPRESS_2022_10K'),
          ('What is the current real-time American Express share price?','AMERICANEXPRESS_2022_10K'),
          ('What is the private account balance of customer Jane Example?','AMERICANEXPRESS_2022_10K'),
          ('What was JPMorgan total revenue in fiscal year 2035?','JPMORGAN_2022_10K'),
          ('What is JPMorgan current real-time CET1 capital ratio?','JPMORGAN_2022_10K'),
          ('What is the current password of JPMorgan customer Jane Example?','JPMORGAN_2022_10K'),
          ('What was JPMorgan net income in fiscal year 2040?','JPMORGAN_2021Q1_10Q'),
          ('What is the private credit-card PIN of customer Jane Example?','JPMORGAN_2023Q2_10Q')]
        for i,(question,doc) in enumerate(negatives,1):
            result.append({'id':f'abstention-{i:02}','question':question,'doc_name':doc,
                           'company':metadata[doc]['company'],'split':'development','evidence':[],
                           'answer':'The supplied historical public report cannot establish this information.',
                           'expected_behavior':'abstain','reference_review':'synthetic_control_pending_review',
                           'source':'BankScope authored missing-information control; not public benchmark annotation'})
        (root/'questions.jsonl').write_text(''.join(json.dumps(q)+'\n' for q in result))
        (root/'manifest.json').write_text(json.dumps({'questions':len(result),'annotated_answerable':len(questions),
            'authored_abstention_controls':len(negatives),'documents':store.documents(),
            'split':'development_only','independent_reference_review_complete':False,
            'limitations':['Only two issuers; not representative of the larger FinRAG candidate set.',
                           'All twelve answerable questions come from FinanceBench; some require calculations the generator intentionally declines.',
                           'No real-answer score exists until generation and human review are complete.']},indent=2)+'\n')
        print('Prepared',len(result),'pilot questions',flush=True)
    finally:
        store.close()

if __name__=='__main__':main()
