"""Index complete development-bank source reports, never reference labels."""
import json
from pathlib import Path
from bankscope.store import Store


def main():
    root=Path('data/benchmarks/finrag-v3')
    store=Store(root/'development.sqlite3')
    reports=json.loads(Path('datasets/development_reports.json').read_text())
    indexed={d['id'] for d in store.documents()}
    try:
        for r in reports:
            path=Path('data/reports/pdfs')/(r['id']+'.pdf')
            if not path.exists() or not path.read_bytes().startswith(b'%PDF-'):
                print(r['company'],'source unavailable',flush=True);continue
            if r['id'] not in indexed:
                result=store.ingest_pdf(path,r['id'],r['company'],r['year'],r['url'],'pdfium')
                print(r['company'],result['pages'],'pages',flush=True)
        (root/'development-corpus.json').write_text(json.dumps({'documents':store.documents(),
             'passages':store.db.execute('select count(*) from passages').fetchone()[0],
             'split':'development_only','labels_indexed':False},indent=2)+'\n')
    finally:store.close()

if __name__=='__main__':main()
