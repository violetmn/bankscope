"""Report readiness without converting missing mappings into passing examples."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def audit(path):
    rows=[json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    ids=[r['id'] for r in rows]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate question IDs')
    issuers={}
    pending=[]
    for row in rows:
        company=row['company'].casefold().strip()
        issuers.setdefault(company,set()).add(row['split'])
        missing=[]
        if not row.get('doc_name'):missing.append('document_id')
        if not row.get('source_url',''):missing.append('source_url')
        evidence=row.get('evidence',[])
        if not evidence or any(type(e.get('evidence_page_num')) is not int or e['evidence_page_num']<0 for e in evidence):missing.append('physical_evidence_page')
        if row.get('reference_review')!='verified':missing.append('reference_review')
        if not row.get('reference_reviewer'):missing.append('reference_reviewer')
        if not row.get('report_sha256') or len(row['report_sha256'])!=64:missing.append('report_sha256')
        if missing:pending.append({'id':row['id'],'company':row['company'],'missing':missing})
    overlaps=[bank for bank,splits in issuers.items() if len(splits)>1]
    return {'question_count':len(rows),'split_counts':dict(Counter(r['split'] for r in rows)),
            'issuer_split_overlap':overlaps,'mapping_or_review_pending':len(pending),
            'ready':bool(rows) and not pending and not overlaps,
            'annotations_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'pending':pending}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('questions');p.add_argument('--output',required=True);a=p.parse_args()
    result=audit(a.questions)
    with open(a.output,'x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='pending'},indent=2))
