"""Narrow input checks for requests outside historical public report coverage."""
import re


def historical_scope_limit(question, hits):
    text=question.casefold()
    live = re.search(r'\b(?:real[ -]?time|right now|today|as of now)\b',text)
    figure = re.search(r'\b(?:price|ratio|capital|balance|revenue|assets|income|deposits)\b',text)
    if live and figure:
        return 'These historical reports cannot establish a live or real-time figure. Ask for a specific reporting period.'
    credentials = re.search(r'\b(?:password|pin)\b',text) and re.search(r'\b(?:customer|cardholder|my|their|account)\b',text)
    policy = re.search(r'\b(?:policy|policies|protect|protection|definition)\b',text)
    if (credentials and not policy) or (
        re.search(r'\bprivate (?:account|customer|cardholder)\b',text)):
        return 'Public annual reports do not provide individual customer credentials or private account information.'
    # Historical actuals are distinct from future schedules, targets and forecasts.
    if re.search(r'\b(?:forecast|projected|expected|target|outlook|maturit\w*|schedule\w*)\b',text):
        return None
    years=[int(x) for x in re.findall(r'\b(?:fiscal year\s*|fy\s*)(20\d{2})\b',text)]
    report_years=[h['year'] for h in hits if type(h.get('year')) is int]
    actuals=re.search(r'\bwhat (?:was|were)\b',text)
    metric=re.search(r'\b(?:revenue|net income|customer deposits|total assets)\b',text)
    if actuals and metric and years and report_years and max(years)>max(report_years):
        return 'The requested fiscal-year actuals are later than the retrieved reports. These sources cannot establish that result.'
    return None
