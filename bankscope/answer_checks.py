"""Conservative, deterministic answer checks, not semantic fact verification."""
import re
from decimal import Decimal

SCALES = {None: Decimal(1), 'thousand': Decimal(1000), 'million': Decimal(10)**6,
          'billion': Decimal(10)**9, 'trillion': Decimal(10)**12}
NUMBER = r'-?\d[\d,]*(?:\.\d+)?'
MONEY = re.compile(r'(?P<currency>USD|CAD|EUR|GBP|\$|€|£)\s*(?P<number>' + NUMBER + r')\s*(?P<scale>thousand|million|billion|trillion)?\b', re.I)


def citation_ids(answer):
    """Include grouped citations, so [S1, S999] cannot bypass ID validation."""
    return set(re.findall(r'\bS(\d+)\b', ' '.join(re.findall(r'\[([^\]]*)\]', answer))))


def default_scale(text):
    match = re.search(r'\(\s*(?:[A-Z]{3}\s+|\$\s*)?(thousands|millions|billions|trillions)\b', text, re.I)
    return match.group(1).lower().rstrip('s') if match else None


def amounts(text, table_scale=None):
    for match in MONEY.finditer(text):
        scale = match['scale'].lower() if match['scale'] else table_scale
        value = Decimal(match['number'].replace(',', '')) * SCALES[scale]
        yield match.group(0).strip(), match['currency'].upper(), value


def numeric_warnings(answer, cited_hits):
    """Check explicit monetary magnitudes against cited text only.

    Passing does NOT verify label/year/entity/currency identity or completeness.
    Derived/rounded amounts can be flagged even when mathematically reasonable.
    """
    warnings = []
    for label, currency, value in amounts(answer):
        supported = False
        for hit in cited_hits:
            text = hit['text']
            scale = default_scale(text)
            direct = {(c, v) for _, c, v in amounts(text, scale)}
            if (currency, value) in direct:
                supported = True
            # Tables commonly show the currency symbol once, then omit it on rows.
            # Only infer a scale from a parenthesized table-unit heading.
            if scale and currency in text.upper():
                values = {Decimal(n.replace(',', '')) * SCALES[scale]
                          for n in re.findall(NUMBER, text)}
                supported |= value in values
        if not supported:
            warnings.append(f'Could not match {label} to an amount in the cited excerpts. Check its unit, currency and source table.')
    return list(dict.fromkeys(warnings))


def reconcile_components(total, components):
    """Exact arithmetic for already structured, same-unit inputs; no text inference.

    This utility is tested for the reported breakdown failure. Automated table-to-row
    mapping is not implemented; generation must not claim this check ran on prose.
    """
    total = Decimal(str(total))
    values = [Decimal(str(value)) for value in components]
    if not total.is_finite() or any(not value.is_finite() for value in values):
        raise ValueError('Amounts must be finite')
    subtotal = sum(values, Decimal(0))
    return {'matches': subtotal == total, 'total': str(total), 'subtotal': str(subtotal),
            'difference': str(total - subtotal)}
