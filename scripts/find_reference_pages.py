"""Suggest numeric source pages for manual inspection; never certifies evidence."""
import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path
import pypdfium2 as pdfium


def find(questions, bank, pdf_path):
    rows=[json.loads(x) for x in Path(questions).read_text().splitlines() if x.strip()]
    selected=[r for r in rows if r['company']==bank]
    if any(r['split']!='development' for r in selected):
        raise ValueError('Do not inspect reserved-test source labels during development')
    pdf=pdfium.PdfDocument(pdf_path)
    try:
        pages=[]
        for i in range(len(pdf)):
            page=pdf[i];textpage=page.get_textpage()
            try:pages.append(textpage.get_text_range())
            finally:textpage.close();page.close()
    finally:pdf.close()
    suggestions=[]
    for row in selected:
        try:value=Decimal(row['reference_value'])
        except Exception:continue
        token=f'{value:,.0f}' if value==value.to_integral() else format(value.normalize(),',f')
        suggestions.append({'id':row['id'],'question':row['question'],'reference_value':row['reference_value'],
                            'matched_token':token,'candidate_physical_pages':[i+1 for i,t in enumerate(pages) if token in t],
                            'status':'numeric_match_only_requires_visual_label_year_unit_check'})
    return {'bank':bank,'report_sha256':hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest(),
            'physical_pages':len(pages),'suggestions':suggestions}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--questions',required=True);p.add_argument('--bank',required=True)
    p.add_argument('--pdf',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    result=find(a.questions,a.bank,a.pdf)
    with open(a.output,'x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
