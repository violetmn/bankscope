"""Import public bank QA values; missing report/page mappings remain explicitly pending."""
import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def read_rows(path):
    with zipfile.ZipFile(path) as z:
        strings=[''.join(e.itertext()) for e in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',NS)]
        rows=[]
        for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//m:row',NS):
            cells={}
            for cell in row.findall('m:c',NS):
                value=cell.find('m:v',NS)
                value=value.text if value is not None else ''
                if cell.attrib.get('t')=='s' and value:
                    value=strings[int(value)]
                cells[re.sub(r'\d','',cell.attrib['r'])]=value
            rows.append(cells)
    headers=rows[0]
    return [{headers[k]:v for k,v in row.items()} for row in rows[1:]]


def prepare(source, destination):
    all_rows=read_rows(source)
    rows=[r for r in all_rows if r['Doc Type']=='Report' and int(float(r['Source Document Year']))==2023]
    banks=sorted({r['Bank'] for r in rows},key=lambda b:hashlib.sha256(('bankscope-v1:'+b).encode()).hexdigest())
    development=set(banks[:max(1,len(banks)//3)]) | ({'JP Morgan'} & set(banks))
    # Round-robin sampling by bank prevents one issuer dominating the candidate list.
    buckets={b:sorted([r for r in rows if r['Bank']==b],key=lambda r:hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()) for b in banks}
    selected=[]
    while len(selected)<min(100,len(rows)):
        for bank in banks:
            if buckets[bank] and len(selected)<100:
                selected.append(buckets[bank].pop(0))
    dest=Path(destination);dest.mkdir(parents=True,exist_ok=False)
    records=[]
    for i,r in enumerate(selected,1):
        records.append({'id':f'finrag-candidate-{i:03}','company':r['Bank'],
                        'split':'development' if r['Bank'] in development else 'reserved_test',
                        'question':r['Query'],'reference_value':r['Value'],
                        'value_year':int(float(r['Year'])),
                        'report_year':int(float(r['Source Document Year'])),
                        'doc_type':r['Doc Type'],'indicator':r['Data'],
                        'numerical':r['Numerical'],'in_table':r['In table'],
                        'unit':'millions in source-document currency; currency unverified',
                        'doc_name':None,'source_url':None,'evidence':[],
                        'reference_review':'pending','mapping_status':'report_and_page_required'})
    (dest/'candidates.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    manifest={'source':'https://github.com/Lsilotto/FinRAG-QA','source_file_sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),
              'source_rows':len(all_rows),'eligible_rows':len(rows),'selection_scope':'2023 annual reports only; comparative value years preserved','candidate_questions':len(records),'banks':len(banks),
              'split_counts':dict(Counter(r['split'] for r in records)),
              'development_banks':sorted(development),'reserved_test_banks':sorted(set(banks)-development),
              'ready_for_evaluation':False,'reason':'Source URLs, document identity, physical evidence pages and reference verification are missing.',
              'independence':'Bank-disjoint split; JPMorgan forced into development because existing diagnostics used that issuer. No reserved-test outcomes inspected. Public values may have model-training exposure.',
              'reuse':'Upstream repository has no explicit license identified; annotations remain local pending reuse review.'}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args();prepare(a.source,a.output)
