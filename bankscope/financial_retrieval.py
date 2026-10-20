"""Retrieve numerical rows with source-page headings, units and period columns.

Rules use question intent and source text only, never diagnostic labels or values.
These excerpts remain unverified evidence, not extracted or calculated answers.
"""
import re
from bankscope.semantic import ready, reranker_ready, distinct_pages

METRICS = [
    ('credit_losses', r'\bprovisions? for (?:credit|loan) losses\b', r'(?:total\s+)?provisions? for (?:\(recovery of\)\s+)?(?:credit|loan) losses(?:\s*\(PCL\))?'),
    ('cet1', r'\b(?:common equity tier\s*1|CET1)\b', r'common equity tier\s*1(?:\s*\(CET1\))?(?:\s+capital)?\s+ratio'),
    ('net_interest_income', r'\bnet interest income\b', r'net interest income'),
    ('net_income', r'\bnet income\b', r'net income'),
    ('revenue', r'\b(?:total\s+)?revenue(?:s)?\b', r'(?:total\s+)?revenues?'),
    ('deposits', r'\bdeposits\b', r'(?:(?:total|customer)\s+)?deposits'),
    ('assets', r'\btotal assets\b', r'(?:total\s+)?assets'),
    ('roe', r'\b(?:return on (?:common )?equity|ROE)\b', r'return on (?:common )?equity(?:\s*\(ROE\))?'),
]
SUMMARY = re.compile(
    r'^\s*(?:t\s*a\s*b\s*l\s*e\s*\d+\s*[|:]?\s*)?'
    r'(?:(?:(?:[a-z]+[- ]year\s+)?summary\s+of\s+)?(?:consolidated\s+)?financial\s+(?:and other\s+)?highlights'
    r'|selected\s+financial(?:\s+and\s+other)?\s+highlights'
    r'|consolidated\s+(?:balance\s+sheets?|statements?\s+of\s+(?:income|earnings|financial\s+position)))\b[^\r\n]*\r?$',
    re.I | re.M)
UNITS = re.compile(r'\b(?:millions?|billions?|thousands?|percent(?:age)?|capital ratios?)\b|%', re.I)
YEARS = re.compile(r'\b20\d{2}\b[^A-Za-z]{1,45}\b20\d{2}\b')


def intent(question):
    text = question.casefold()
    # Specialized measures and comparisons keep the established general retriever.
    if re.search(r'\b(?:segments?|average|quarter|q[1-4]|compare|why|explain|attributable|available)\b|period.end|how (?:does|do)', text):
        return None
    matches = [m for m in METRICS if re.search(m[1], text, re.I)]
    if 'net revenue' in text or re.search(r'per share|shareholders', text):
        return None
    if len(matches) != 1:
        return None
    return matches[0]


def metric_lines(text, metric, question):
    label = metric[2]
    if re.search(r'\badjusted\b', question, re.I):
        label = r'(?:adjusted\s+' + label + '|' + label + r'\s*[-–]?\s*adjusted)'
    else:
        label += r'(?:\s*[-–]\s*reported)?'
    pattern = re.compile(r'(?<!\w)' + label + r'\s*(?:\([a-z0-9, ]+\))?\s*', re.I)
    lines = text.splitlines()
    matches = []
    for i, line in enumerate(lines):
        match = pattern.search(line)
        prefix = line[:match.start()].rstrip(' \t:-–—') if match else ''
        if prefix and prefix[-1].isalpha():
            continue
        if match and re.match(r'[$\s(\d,\.\-–%]+\d', line[match.end():]):
            matches.append(i)
    return lines, matches


def excerpt(lines, matched):
    # Keep column headings and nearby rows; do not insert inferred financial facts.
    selected = set(range(min(7, len(lines))))
    for i, line in enumerate(lines):
        if SUMMARY.search(line):
            selected.add(i)
    for i in matched[:4]:
        selected.update(range(max(0, i-2), min(len(lines), i+4)))
        prior = [j for j in range(i) if UNITS.search(lines[j])]
        if prior:
            j = prior[-1]
            selected.update(range(max(0, j-1), j+1))
    output, previous = [], -1
    for i in sorted(selected):
        if previous >= 0 and i > previous+1:
            output.append('[...]')
        output.append(lines[i]); previous = i
    return '\n'.join(output)[:5000]


def table_candidates(store, question, metric, company, year, doc_id):
    conditions, args = [], []
    for field, value in [('company', company), ('year', year), ('id', doc_id)]:
        if value is not None:
            conditions.append('d.'+field+'=?'); args.append(value)
    sql = '''SELECT c.text,c.doc_id,c.page,d.company,d.year,d.url
             FROM page_contexts c JOIN documents d ON d.id=c.doc_id'''
    if conditions:
        sql += ' WHERE '+' AND '.join(conditions)
    candidates = []
    for row in store.db.execute(sql, args):
        text = row['text']
        lines, matched = metric_lines(text, metric, question)
        # Require a recognizable group statement, column years and stated units.
        heading = SUMMARY.search(text)
        periods = list(YEARS.finditer(text))
        period_matches = bool(periods) and (year is None or any(re.search(r'\b'+str(year)+r'\b', m[0]) for m in periods))
        nonconsolidated = re.search(r'pro forma|parent company only|condensed financial (?:statements|information) of (?:the )?parent', text, re.I)
        if not matched or not heading or not period_matches or not UNITS.search(text) or nonconsolidated:
            continue
        numeric_rows = sum(bool(re.search(r'\d[\d,.%]*\s+\(?\d', line)) for line in lines)
        if numeric_rows < 3:
            continue
        hit = dict(row)
        hit['text'] = excerpt(lines, matched)
        hit['chunk_id'] = f"{hit['doc_id']}:p{hit['page']}:financial"
        hit['citation'] = f"[{hit['doc_id']}, PDF page {hit['page']}]"
        hit['source_url'] = hit['url'].split('#')[0]+f"#page={hit['page']}" if hit['url'] else ''
        hit['source_kind'] = 'financial_table_excerpt'
        hit['table_family'] = 'highlights' if re.search('highlights|selected financial', heading[0], re.I) else 'statement'
        hit['financial_score'] = 4*bool(re.search('highlights', heading[0], re.I)) + min(numeric_rows, 10)/10
        candidates.append(hit)
    return sorted(candidates, key=lambda h: (-h['financial_score'], h['doc_id'], h['page']))


def search(store, question, k, company=None, year=None, doc_id=None):
    metric = intent(question)
    scoped_company, scoped_year, scoped_doc = company, year, doc_id
    candidates = []
    if metric:
        from bankscope.focused_retrieval import resolve_scope
        scoped_company, scoped_year, scoped_doc = resolve_scope(question, store.documents(), company, year, doc_id)
        candidates = table_candidates(store, question, metric, scoped_company, scoped_year, scoped_doc)
    base = 'rerank' if ready(store) and reranker_ready() else 'dense' if ready(store) else 'bm25'
    # Retain ordinary retrieval evidence after at most two high-confidence table pages.
    preferred = candidates[:1]
    if preferred and k > 1:
        different = next((h for h in candidates[1:] if h['table_family'] != preferred[0]['table_family']), None)
        if different is not None:
            preferred.append(different)
        elif len(candidates) > 1:
            preferred.append(candidates[1])
    if len(preferred) == k:
        return preferred
    fallback = store.search(question, k, scoped_company, scoped_year, scoped_doc, strategy=base)
    return distinct_pages(preferred+fallback, k)
