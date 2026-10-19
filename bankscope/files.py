"""Local source lookup under fixed roots; callers must also check registration."""
import re
from pathlib import Path


def report_path(doc_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', doc_id):
        return None
    for directory in [Path('data/reports/pdfs'), Path('data/financebench/pdfs')]:
        path = directory / f'{doc_id}.pdf'
        if path.is_file():
            return path
    return None
