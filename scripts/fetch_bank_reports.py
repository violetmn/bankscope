"""Download the explicitly curated bank reports; keep publisher PDFs gitignored."""
import hashlib
import json
from pathlib import Path
from fetch_financebench import download


def main():
    catalog = json.loads(Path('datasets/bank_reports.json').read_text())
    documents = []
    for item in catalog['documents']:
        target = Path('data/reports/pdfs') / f"{item['doc_id']}.pdf"
        download(item['url'], target, pdf=True, user_agent='Mozilla/5.0')
        documents.append({**item, 'local_path': str(target),
                          'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
        print('Downloaded', item['doc_id'], flush=True)
    target = Path('data/reports/manifest.json')
    target.write_text(json.dumps({**catalog, 'documents': documents}, indent=2)+'\n')
    print('Manifest:', target)


if __name__ == '__main__':
    main()
