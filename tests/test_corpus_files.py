from pathlib import Path
import pytest
from bankscope.files import report_path


@pytest.mark.parametrize('doc_id',['../secret','a/b','a?x=1','a#page=1','/private/secret'])
def test_report_paths_cannot_escape_roots(doc_id):
    assert report_path(doc_id) is None


def test_bank_reports_and_existing_financebench_sources_both_resolve(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    for root,doc in [('data/reports/pdfs','BANK_2023'),('data/financebench/pdfs','LEGACY_2022')]:
        path=Path(root)/f'{doc}.pdf';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
        assert report_path(doc)==path
    assert report_path('ABSENT') is None
