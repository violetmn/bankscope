"""JPMorgan's four-column deposit-by-segment layout.

Uses row/column geometry and headers, not embedded financial answers. The first
two columns are period-end; the two Average columns are validated separately.
"""
import hashlib
import json
import re
from pathlib import Path
from bankscope.answer_checks import reconcile_components

TABLE_ID = 'customer_deposits_by_segment_period_end'
NUMERIC = re.compile(r'-?\d[\d,]*(?:\.\d+)?')


def word_lines(words, tolerance=2):
    lines = []
    for word in sorted(words, key=lambda w: (w['top'], w['x0'])):
        if not lines or abs(word['top']-lines[-1][0]['top']) > tolerance:
            lines.append([word])
        else:
            lines[-1].append(word)
    return [sorted(line, key=lambda w:w['x0']) for line in lines]


def parse_segment_words(words, page_text):
    normalized = ' '.join(page_text.casefold().split())
    if 'period-end and average deposit balances' not in normalized:
        raise ValueError('Not the supported period-end/average deposit table')
    lines = word_lines(words)
    candidates = []
    for index, line in enumerate(lines):
        text = ' '.join(w['text'] for w in line)
        if '(in millions)' not in text.casefold():
            continue
        columns = [w for w in line if re.fullmatch(r'20\d{2}', w['text'])]
        if len(columns) != 4 or [w['text'] for w in columns[:2]] != [w['text'] for w in columns[2:]]:
            continue
        if columns[0]['text'] == columns[1]['text']:
            raise ValueError('Year columns must be distinct')
        # An Average heading must be positioned over the right-hand column pair.
        above = [w for row in lines[max(0,index-2):index] for w in row if w['text'].casefold()=='average']
        if not any(w['x0'] > columns[1]['x1'] and w['x0'] < columns[3]['x1'] for w in above):
            raise ValueError('Average-column header is missing or ambiguous')
        rows = []
        totals = None
        for row in lines[index+1:]:
            numbers = [w for w in row if NUMERIC.fullmatch(w['text'])]
            if len(numbers) != 4:
                raise ValueError('Expected four unambiguous financial values per segment row')
            if any(abs(value['x1']-header['x1']) > 8 for value,header in zip(numbers,columns)):
                raise ValueError('Financial values do not align with year headers')
            label = ' '.join(w['text'] for w in row if w['x1'] < numbers[0]['x0'] and w['text'] != '$')
            if not label:
                raise ValueError('Missing segment label')
            values = [n['text'].replace(',','') for n in numbers]
            if label.casefold()=='total firm':
                if not any(w['text']=='$' for w in row):
                    raise ValueError('Currency symbol missing')
                totals = values
                break
            rows.append({'label':label, 'raw_values':values})
        if not rows or totals is None or len({r['label'] for r in rows}) != len(rows):
            raise ValueError('Incomplete or duplicated segment rows')
        checks = [reconcile_components(totals[i], [r['raw_values'][i] for r in rows]) for i in range(4)]
        if not all(check['matches'] for check in checks):
            raise ValueError('Segment rows do not reconcile in all four columns')
        years = [int(w['text']) for w in columns[:2]]
        candidates.append({'years':years,
            'rows':[{'label':r['label'],'values':dict(zip(map(str,years),r['raw_values'][:2]))} for r in rows],
            'totals':dict(zip(map(str,years),totals[:2])),
            'reconciliation':dict(zip(map(str,years),checks[:2])),
            'average_totals_not_used':dict(zip(map(str,years),totals[2:])),
            'average_columns_reconcile':all(c['matches'] for c in checks[2:])})
    if len(candidates) != 1:
        raise ValueError('Expected one supported four-column segment table')
    return candidates[0]


def locate_segment_page(path):
    """Locate by text markers; page numbers are not tied to a reporting year."""
    import pypdfium2
    candidates = []
    with pypdfium2.PdfDocument(path) as pdf:
        for index in range(len(pdf)):
            page = pdf[index]
            try:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_bounded()
                finally:
                    textpage.close()
            finally:
                page.close()
            if all(marker in text for marker in ['Total Firm','Consumer & Community Banking','period-end and average deposit balances']):
                candidates.append(index+1)
    if len(candidates) != 1:
        raise ValueError('Segment deposit source page is missing or ambiguous')
    return candidates[0]


def extract_segment_deposits(store, path, doc_id, page_number=None):
    import pdfplumber
    documents = {d['id']:d for d in store.documents()}
    if doc_id not in documents:
        raise ValueError('Ingest the source report first')
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if digest != documents[doc_id]['sha256']:
        raise ValueError('Source checksum differs from indexed report')
    page_number = page_number or locate_segment_page(path)
    with pdfplumber.open(path) as pdf:
        if not 1 <= page_number <= len(pdf.pages):
            raise ValueError('PDF page outside document')
        page = pdf.pages[page_number-1].dedupe_chars()
        table = parse_segment_words(page.extract_words(), page.extract_text() or '')
    data = {**table,'table_id':TABLE_ID,'doc_id':doc_id,'company':documents[doc_id]['company'],
        'report_year':documents[doc_id]['year'],'pdf_page':page_number,'source_sha256':digest,
        'title':'Period-end deposits by business segment','metric_label':'Period-end deposits',
        'category_label':'Business segment','category_basis':'business_segment','total_label':'Total Firm',
        'unit':'millions','currency_symbol':'$','currency_note':'Dollar symbol as printed; no inferred currency code.',
        'source_url':f'/reports/{doc_id}.pdf#page={page_number}',
        'extraction_scope':'JPMorgan four-column segment deposit layout; average columns excluded from period-end results.'}
    with store.db:
        store.db.execute('INSERT OR REPLACE INTO report_tables VALUES(?,?,?)',(doc_id,TABLE_ID,json.dumps(data)))
    return data
