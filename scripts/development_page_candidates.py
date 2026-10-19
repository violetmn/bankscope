"""Numeric/scale suggestions for development review only; never evidence certification."""
import json
import re
from decimal import Decimal
from pathlib import Path
import pypdfium2 as pdfium


def main():
    root=Path('data/benchmarks/finrag-v3');out=[]
    questions=[q for q in map(json.loads,(root/'candidates.jsonl').read_text().splitlines()) if q['split']=='development' and not q['evidence']]
    reports=json.loads(Path('datasets/development_reports.json').read_text())
    for report in reports:
        selected=[q for q in questions if q['company']==report['company']]
        if not selected:continue
        path=Path('data/reports/pdfs')/(report['id']+'.pdf')
        if not path.read_bytes().startswith(b'%PDF-'):continue
        pdf=pdfium.PdfDocument(path);pages=[]
        try:
            for i in range(len(pdf)):
                p=pdf[i];t=p.get_textpage()
                try:pages.append(t.get_text_bounded())
                finally:t.close();p.close()
        finally:pdf.close()
        (root/(report['id']+'-pages.json')).write_text(json.dumps(pages))
        for q in selected:
            value=Decimal(q['reference_value']);matches=[]
            for scale in [1,1000]:
                v=value*scale
                for label,token in [('comma',format(v.normalize(),',f')),('space',format(v.normalize(),',f').replace(',',' ')),('plain',format(v.normalize(),'f'))]:
                    regex=r'(?<![\d.,])'+re.escape(token)+r'(?![\d.,])'
                    nums=[i+1 for i,text in enumerate(pages) if re.search(regex,text)]
                    if nums:matches.append({'source_scale_factor':scale,'format':label,'token':token,'physical_pages':nums})
            out.append({'id':q['id'],'company':q['company'],'indicator':q['indicator'],'reference_value':q['reference_value'],'matches':matches})
            print(q['id'],q['company'],q['indicator'],[(m['source_scale_factor'],m['physical_pages'][:20]) for m in matches],flush=True)
    (root/'development-page-candidates.json').write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':main()
