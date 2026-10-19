"""Explicitly scoped deposit-table extraction; never infer a complete table from prose."""
import hashlib
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from bankscope.answer_checks import reconcile_components

TABLE_ID = 'customer_deposits_by_type'


def parse_deposit_rows(raw, years):
    if len(years) != 2 or len(set(years)) != 2:
        raise ValueError('Expected two distinct year columns')
    rows, group, totals = [], None, None
    for row in raw:
        if not row or not row[0]:
            raise ValueError('A table row has no label')
        label = ' '.join(row[0].split())
        cells = ' '.join(str(cell) for cell in row[1:] if cell)
        numbers = re.findall(r'(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\w.])', cells)
        if not numbers:
            if label.endswith(':'):
                group = label.rstrip(':')
                continue
            raise ValueError('Missing numeric cells: ' + label)
        if len(numbers) != len(years):
            raise ValueError('Ambiguous year columns: ' + label)
        values = {str(year): str(Decimal(number.replace(',', ''))) for year, number in zip(years, numbers)}
        if label.casefold() == 'total customer deposits':
            if totals is not None:
                raise ValueError('Duplicate total')
            totals = values
            continue
        if totals is not None:
            raise ValueError('Unexpected rows after total')
        # Subcategories only inherit the certificate heading; sweep accounts do not.
        full_label = f'{group} / {label}' if group and label.casefold() in {'direct', 'third-party (brokered)'} else label
        rows.append({'label': full_label, 'values': values})
    if not rows or totals is None or len({r['label'] for r in rows}) != len(rows):
        raise ValueError('Incomplete table or duplicate row labels')
    checks = {str(year): reconcile_components(totals[str(year)], [r['values'][str(year)] for r in rows]) for year in years}
    if not all(check['matches'] for check in checks.values()):
        raise ValueError('Extracted categories do not reconcile with reported total')
    return {'years': list(years), 'rows': rows, 'totals': totals, 'reconciliation': checks}


def extract_deposits(store, path, doc_id, page_number):
    import pdfplumber
    documents = {d['id']: d for d in store.documents()}
    if doc_id not in documents:
        raise ValueError('Ingest the document first')
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if digest != documents[doc_id]['sha256']:
        raise ValueError('PDF checksum differs from indexed document; reingest it first')
    with pdfplumber.open(path) as pdf:
        if not 1 <= page_number <= len(pdf.pages):
            raise ValueError('PDF page outside document')
        page = pdf.pages[page_number-1]
        matches = []
        for candidate in page.find_tables():
            raw = candidate.extract()
            if raw and raw[0] and (raw[0][0] or '').strip() == 'Savings and transaction accounts':
                # Read the heading immediately above this table, not another table's years.
                context = page.crop((0, max(0, candidate.bbox[1]-38), page.width, candidate.bbox[1])).extract_text() or ''
                headers = re.findall(r'^\(Millions\)[ \t]+(20\d{2})[ \t]+(20\d{2})[ \t]*$', context, flags=re.M)
                if len(headers) != 1:
                    raise ValueError('Could not unambiguously read units and year headers')
                if '$' not in ' '.join(str(c) for row in raw for c in row if c):
                    raise ValueError('Currency symbol missing; do not infer currency')
                matches.append(parse_deposit_rows(raw, [int(y) for y in headers[0]]))
    if len(matches) != 1:
        raise ValueError('Expected exactly one supported deposit-type table on this page')
    data = {**matches[0], 'table_id': TABLE_ID, 'doc_id': doc_id, 'company': documents[doc_id]['company'],
            'report_year': documents[doc_id]['year'], 'pdf_page': page_number, 'source_sha256': digest,
            'title': 'Customer deposits by deposit type', 'unit': 'millions', 'currency_symbol': '$',
            'currency_note': 'Dollar symbol as printed in source; no currency-code inference or FX conversion.',
            'source_url': f'/reports/{doc_id}.pdf#page={page_number}',
            'extraction_scope': 'Deposit-type table with two year columns; not a general financial-table extractor.'}
    with store.db:
        store.db.execute('INSERT OR REPLACE INTO report_tables VALUES(?,?,?)', (doc_id, TABLE_ID, json.dumps(data)))
    return data


def table_analysis(store, question, company=None, report_year=None):
    """Handle a small, explicit set of deposit lookup/breakdown/change requests."""
    q = ' '.join(question.casefold().strip(' ?.').split())
    if not re.search(r'\b(?:customer deposits|deposits by deposit type|period-end deposits|deposits by business segment)\b', q):
        return None
    if re.search(r'\b(why|cause|forecast|predict|interest|maturit|risk|recommend|liabilit|revenue)', q):
        return None
    comparison = bool(re.search(r'\b(change|changed|grow|grew|growth|increase|increased|compare|difference)\b', q))
    lookup = bool(re.match(r'(what (?:were|was|are|is|does)|how much (?:were|was|are)|show|give|break down|breakdown)', q))
    if not comparison and not lookup:
        return None
    records = store.db.execute('SELECT t.data FROM report_tables t JOIN documents d ON t.doc_id=d.id WHERE (? IS NULL OR d.company=?) AND (? IS NULL OR d.year=?)',
        (company, company, report_year, report_year)).fetchall()
    if len(records) != 1:
        return None  # Ambiguous company/report selection needs normal research, not a guess.
    table = json.loads(records[0]['data'])
    if table.get('category_basis') == 'business_segment' and 'deposit type' in q:
        return None  # Segment balances are not a product-type breakdown.
    if table.get('category_basis') != 'business_segment' and 'business segment' in q:
        return None
    # Do not apply a total-table answer to a different entity, geography, product,
    # or multi-metric question just because it mentions customer deposits.
    scoped_q = re.sub(re.escape(table['company'].casefold()) + r"(?:'s|’s)?", '', q)
    permitted = set('what were was are is how much did does the report say about show give me a break down breakdown total customer period-end deposits by deposit type business segment in for as of at year from to and between compare change changed grow grew growth increase increased difference'.split())
    if any(token not in permitted and not re.fullmatch(r'(?:19|20)\d{2}', token) for token in re.findall(r"[\w'-]+", scoped_q)):
        return None
    requested = list(dict.fromkeys(int(y) for y in re.findall(r'\b(?:19|20)\d{2}\b', q)))
    available = table['years']
    if any(year not in available for year in requested):
        return {'status': 'unsupported_period', 'answer': f'This extracted table only reports {", ".join(map(str,available))}. It cannot answer the requested period.', 'table': table}
    years = requested or (sorted(available) if comparison else [max(available)])
    if comparison and len(years) != 2:
        return {'status': 'needs_periods', 'answer': 'Choose two years reported in the table for a comparison.', 'table': table}
    citation = f'[{table["doc_id"]}, PDF page {table["pdf_page"]}]'
    metric = table.get('metric_label', 'Customer deposits')
    result = {'status': 'calculated_from_table', 'table': table, 'selected_years': years,
              'note': 'Rows, year headers and exact category sums checked; source interpretation still needs review.'}
    if comparison:
        direction = re.search(r'\bfrom\s+((?:19|20)\d{2})\s+to\s+((?:19|20)\d{2})\b', q)
        earlier, later = map(int, direction.groups()) if direction else sorted(years)
        start, end = (Decimal(table['totals'][str(y)]) for y in [earlier,later])
        change = end-start
        percent = ((change/start)*100).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP) if start != 0 else None
        result['calculation'] = {'from_year': earlier, 'to_year': later, 'from_value': str(start), 'to_value': str(end),
                                 'absolute_change': str(change), 'percentage_change': str(percent) if percent is not None else None,
                                 'formula': '(later - earlier) / earlier × 100', 'unit': table['unit']}
        result['answer'] = f'{metric} changed from ${start:,.0f} million in {earlier} to ${end:,.0f} million in {later}: a change of ${change:,.0f} million' + (f' ({percent}%). ' if percent is not None else '; percentage change is undefined with a zero starting value. ') + citation
    else:
        result['answer'] = '\n'.join(f'{metric} in {year}: ${Decimal(table["totals"][str(year)]):,.0f} million. All categories are shown below and sum to the reported total. {citation}' for year in years)
    return result
