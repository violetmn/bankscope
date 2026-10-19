"""Download curated development reports only; validate PDFs and record failures."""
import hashlib
import json
import subprocess
from pathlib import Path


def main():
    reports=json.loads(Path('datasets/development_reports.json').read_text())
    out=[]
    for r in reports:
        path=Path('data/reports/pdfs')/(r['id']+'.pdf')
        if not path.exists() or not path.read_bytes().startswith(b'%PDF-'):
            result=subprocess.run(['curl','-L','--fail','--silent','--show-error','--max-time','90',r.get('download_url',r['url']),'-o',str(path)],capture_output=True,text=True)
            if result.returncode:
                out.append({**r,'status':'download_failed','curl_exit':result.returncode})
                print(r['company'],'download failed',result.returncode,flush=True);continue
        if not path.read_bytes().startswith(b'%PDF-'):
            out.append({**r,'status':'invalid_pdf'});print(r['company'],'not PDF',flush=True);continue
        out.append({**r,'status':'downloaded','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'local_path':str(path)})
        print(r['company'],'downloaded',flush=True)
    dest=Path('data/benchmarks/finrag-v3/development-source-manifest.json')
    dest.write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':main()
