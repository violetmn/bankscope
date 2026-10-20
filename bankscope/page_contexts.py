"""Backfill line-preserving source pages without changing chunks, vectors or tables."""
import hashlib
from bankscope.files import report_path


def prepare(store):
    import pypdfium2
    prepared = []
    for doc in store.documents():
        count = store.db.execute('SELECT COUNT(*) FROM page_contexts WHERE doc_id=?', (doc['id'],)).fetchone()[0]
        if count == doc['pages']:
            continue
        path = report_path(doc['id'])
        if path is None:
            raise ValueError(f"Local source PDF unavailable for {doc['id']}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != doc['sha256']:
            raise ValueError(f"Source PDF differs from indexed report: {doc['id']}")
        with pypdfium2.PdfDocument(path) as pdf:
            if len(pdf) != doc['pages']:
                raise ValueError('Source page count differs from indexed report')
            pages = []
            for i in range(len(pdf)):
                page = pdf[i]
                try:
                    textpage = page.get_textpage()
                    try:
                        pages.append(textpage.get_text_bounded() or '')
                    finally:
                        textpage.close()
                finally:
                    page.close()
        with store.db:
            store.db.execute('DELETE FROM page_contexts WHERE doc_id=?', (doc['id'],))
            store.db.executemany('INSERT INTO page_contexts VALUES(?,?,?)',
                                [(doc['id'], i, text) for i, text in enumerate(pages, 1)])
        prepared.append(doc['id'])
    return {'prepared_reports': prepared, 'pages': store.db.execute('SELECT COUNT(*) FROM page_contexts').fetchone()[0], 'paid_calls': 0}
