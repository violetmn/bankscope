from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch
import hashlib
import pytest
from bankscope.store import Store
from bankscope.segment_tables import locate_segment_page, extract_segment_deposits
from test_segment_tables import words_fixture, PAGE_TEXT


class FakePDF:
    def __init__(self,texts):
        self.texts=texts
        self.pages=[Mock() for _ in texts]
        for page,text in zip(self.pages,texts):
            page.get_textpage.return_value.get_text_bounded.return_value=text
    def __len__(self):return len(self.pages)
    def __getitem__(self,index):return self.pages[index]


def test_pdfium_ingestion_preserves_page_ids_and_closes_resources(tmp_path):
    path=tmp_path/'source.pdf';path.write_bytes(b'mocked PDF bytes')
    pdf=FakePDF(['Cover','Deposits were 50 million.',''])
    store=Store(str(tmp_path/'index.sqlite3'))
    try:
        with patch('pypdfium2.PdfDocument',return_value=nullcontext(pdf)):
            result=store.ingest_pdf(path,'BANK','Example',2023,'https://example.org/a.pdf',extractor='pdfium')
        assert result['pages']==3 and result['empty_pages']==1
        assert store.search('deposits')[0]['page']==2
        for page in pdf.pages:
            page.close.assert_called_once()
            page.get_textpage.return_value.close.assert_called_once()
    finally:store.close()


def test_unsupported_pdf_backend_rejected(tmp_path):
    store=Store(str(tmp_path/'index.sqlite3'))
    try:
        with pytest.raises(ValueError,match='extractor'):
            store.ingest_pdf(tmp_path/'x.pdf','X','Example',2023,'',extractor='unknown')
    finally:store.close()


@pytest.mark.parametrize('matches',[0,1,2])
def test_source_page_locator_requires_exactly_one_marker_match(matches):
    marker='Total Firm Consumer & Community Banking period-end and average deposit balances'
    pdf=FakePDF(['Cover']+[marker]*matches)
    with patch('pypdfium2.PdfDocument',return_value=nullcontext(pdf)):
        if matches==1:assert locate_segment_page('fixture.pdf')==2
        else:
            with pytest.raises(ValueError,match='ambiguous'):locate_segment_page('fixture.pdf')
    for page in pdf.pages:page.close.assert_called_once()


def test_segment_extraction_contract_without_downloads(tmp_path):
    path=tmp_path/'source.pdf';path.write_bytes(b'mock source')
    page=SimpleNamespace(extract_words=words_fixture,extract_text=lambda:PAGE_TEXT)
    page.dedupe_chars=lambda:page
    store=Store(str(tmp_path/'index.sqlite3'))
    try:
        store.add('DOC','Example',2023,'',['Register'],hashlib.sha256(path.read_bytes()).hexdigest())
        with patch('pdfplumber.open',return_value=nullcontext(SimpleNamespace(pages=[page]))):
            data=extract_segment_deposits(store,path,'DOC',1)
        assert data['totals']=={'2023':'12','2022':'14'}
        assert data['category_basis']=='business_segment'
        assert store.db.execute('SELECT COUNT(*) FROM report_tables').fetchone()[0]==1
    finally:store.close()
