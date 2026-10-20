"""Index downloaded catalog reports; preserve unchanged reports and their tables."""
import argparse
import hashlib
import json
from pathlib import Path
from bankscope.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/index.sqlite3')
    parser.add_argument('--embed', action='store_true', help='Build local BGE embeddings after ingestion')
    parser.add_argument('--extractor', choices=['pdfplumber', 'pdfium'], default='pdfium')
    parser.add_argument('--embedding-threads', type=int, default=2, choices=range(1, 17), metavar='1-16')
    args = parser.parse_args()
    catalog = json.loads(Path('datasets/bank_reports.json').read_text())
    store = Store(args.db)
    try:
        existing = {d['id']: d for d in store.documents()}
        for report in catalog['documents']:
            path = Path('data/reports/pdfs') / (report['doc_id'] + '.pdf')
            if not path.is_file() or not path.read_bytes().startswith(b'%PDF-'):
                raise ValueError(f"Missing or invalid PDF: {path}; run scripts/fetch_bank_reports.py first")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            previous = existing.get(report['doc_id'])
            if previous and all(previous[k] == v for k, v in {
                'sha256': digest, 'company': report['company'],
                'year': report['year'], 'url': report['url'],
            }.items()):
                print('Unchanged:', report['doc_id'], flush=True)
                continue
            result = store.ingest_pdf(path, report['doc_id'], report['company'],
                                      report['year'], report['url'], args.extractor)
            print(json.dumps(result), flush=True)
        if args.embed:
            from bankscope.semantic import prepare
            print(json.dumps(prepare(store, threads=args.embedding_threads)), flush=True)
        print(json.dumps({'reports': len(store.documents()),
                          'pages': sum(d['pages'] for d in store.documents()),
                          'passages': store.db.execute('SELECT COUNT(*) FROM passages').fetchone()[0]}), flush=True)
    finally:
        store.close()


if __name__ == '__main__':
    main()
