import copy
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from bankscope.api import app
from bankscope.store import Store
from bankscope.tables import TABLE_ID, parse_deposit_rows, extract_deposits, table_analysis

# Numeric facts transcribed from the visually reviewed source table, physical PDF
# page 123 / printed 120. No source PDFs or benchmark answers are required in CI.
RAW = [
 ['Savings and transaction accounts','$','76,731','','$','66,142'],
 ['Certificates of deposit:','',None,'','',None],
 ['Direct','2,765',None,'','1,415',None],
 ['Third-party (brokered)','13,331',None,'','3,095',None],
 ['Sweep accounts — Third-party (brokered)','16,297',None,'','12,658',None],
 ['Other deposits','71',None,'','42',None],
 ['Card Member credit balances','1,044',None,'','1,030',None],
 ['Total customer deposits','$','110,239','','$','84,382'],
]


@pytest.fixture
def store(tmp_path):
    db=Store(str(tmp_path/'index.sqlite3'))
    db.add('BANK_2022','Example Bank',2022,'https://example.org/report.pdf',['Customer deposits'],'hash')
    data={**parse_deposit_rows(RAW,[2022,2021]),'table_id':TABLE_ID,'doc_id':'BANK_2022',
          'company':'Example Bank','report_year':2022,'pdf_page':123,'source_sha256':'hash',
          'title':'Customer deposits by deposit type','unit':'millions','currency_symbol':'$',
          'source_url':'/reports/BANK_2022.pdf#page=123'}
    with db.db:
        db.db.execute('INSERT INTO report_tables VALUES(?,?,?)',('BANK_2022',TABLE_ID,json.dumps(data)))
    yield db
    db.close()


def test_exact_rows_and_years_survive_extraction():
    data=parse_deposit_rows(RAW,[2022,2021])
    assert len(data['rows'])==6
    assert data['rows'][0]['values']=={'2022':'76731','2021':'66142'}
    assert data['rows'][3]['values']=={'2022':'16297','2021':'12658'}
    assert not data['rows'][3]['label'].startswith('Certificates of deposit /')
    assert data['totals']=={'2022':'110239','2021':'84382'}
    assert all(c['matches'] for c in data['reconciliation'].values())


def test_omitted_sweep_category_fails_closed():
    with pytest.raises(ValueError,match='reconcile'):
        parse_deposit_rows([r for r in RAW if not r[0].startswith('Sweep')],[2022,2021])


@pytest.mark.parametrize('mutation',['missing_total','duplicate_total','extra_number','missing_value','duplicate_label','after_total'])
def test_ambiguous_or_incomplete_tables_rejected(mutation):
    raw=copy.deepcopy(RAW)
    if mutation=='missing_total':raw.pop()
    elif mutation=='duplicate_total':raw.append(raw[-1])
    elif mutation=='extra_number':raw[0].append('999')
    elif mutation=='missing_value':raw[2][1]=''
    elif mutation=='duplicate_label':raw[3][0]='Direct'
    elif mutation=='after_total':raw.append(['Extra category','0','0'])
    with pytest.raises(ValueError):parse_deposit_rows(raw,[2022,2021])


@pytest.mark.parametrize('years',[[2022],[2022,2022],[2022,2021,2020]])
def test_ambiguous_year_headers_rejected(years):
    with pytest.raises(ValueError):parse_deposit_rows(RAW,years)


@pytest.mark.parametrize('question',[
    'Break down customer deposits in 2022',
    'What were total customer deposits in 2022?',
    'What does the report say about customer deposits?',
    'Show Example Bank customer deposits by deposit type',
])
def test_supported_questions_use_table(store,question):
    result=table_analysis(store,question,'Example Bank',2022)
    assert result['status']=='calculated_from_table'
    assert result['selected_years']==[2022]
    assert len(result['table']['rows'])==6


def test_growth_calculation_uses_correct_columns_and_decimal_rounding(store):
    result=table_analysis(store,'How much did customer deposits increase from 2021 to 2022?','Example Bank',2022)
    assert result['calculation']['absolute_change']=='25857'
    assert result['calculation']['percentage_change']=='30.64'


def test_reverse_comparison_preserves_explicit_direction(store):
    result=table_analysis(store,'Compare customer deposits from 2022 to 2021','Example Bank',2022)
    assert result['calculation']['from_year']==2022
    assert result['calculation']['absolute_change']=='-25857'


def test_unsupported_year_is_not_silently_substituted(store):
    result=table_analysis(store,'What were customer deposits in 2025?','Example Bank',2022)
    assert result['status']=='unsupported_period'


@pytest.mark.parametrize('question',[
    'Why did customer deposits increase?',
    'What were customer deposits in Europe?',
    'What were customer deposits at Other Bank?',
    'What were customer deposits and total assets?',
    'What were certificates of deposit maturities in 2025?',
    'What were customer deposits at an interest rate of 5 percent?',
])
def test_out_of_scope_questions_do_not_get_a_total_answer(store,question):
    assert table_analysis(store,question,'Example Bank',2022) is None


def test_company_and_report_filters_are_respected(store):
    assert table_analysis(store,'Show customer deposits','Other Bank',2022) is None
    assert table_analysis(store,'Show customer deposits','Example Bank',2021) is None


def test_reingestion_removes_stale_tables(store):
    store.add('BANK_2022','Example Bank',2022,'',['Changed report'],'newhash')
    assert table_analysis(store,'Show customer deposits','Example Bank',2022) is None


def test_table_api_bypasses_provider_even_when_ai_requested(store):
    path=store.db.execute('PRAGMA database_list').fetchone()['file']
    with patch('bankscope.api.Store',side_effect=lambda:Store(path)),patch('bankscope.api.generate') as provider:
        result=TestClient(app).post('/query',json={'question':'Break down customer deposits in 2022','company':'Example Bank','year':2022,'generate_answer':True})
    assert result.status_code==200
    assert result.json()['mode']=='structured_table'
    provider.assert_not_called()


@pytest.mark.parametrize('case',['valid','ambiguous_years','missing_currency','missing_table','duplicate_table','wrong_page'])
def test_extraction_contract_without_a_downloaded_pdf(tmp_path,case):
    from types import SimpleNamespace
    import hashlib
    path=tmp_path/'fixture.pdf';path.write_bytes(b'local fixture bytes; parser is mocked')
    db=Store(str(tmp_path/'mock.sqlite3'))
    try:
        db.add('TEST','Example Bank',2022,'',['Registration'],hashlib.sha256(path.read_bytes()).hexdigest())
        raw=copy.deepcopy(RAW)
        if case=='missing_currency':
            raw=[[cell.replace('$','') if isinstance(cell,str) else cell for cell in row] for row in raw]
        candidate=SimpleNamespace(bbox=(0,100,500,300),extract=lambda:raw)
        candidates=[] if case=='missing_table' else [candidate]*(2 if case=='duplicate_table' else 1)
        header='(Millions) 2022 2021 2020' if case=='ambiguous_years' else '(Millions) 2022 2021'
        page=SimpleNamespace(width=500,find_tables=lambda:candidates,crop=lambda bbox:SimpleNamespace(extract_text=lambda:header))
        pdf=SimpleNamespace(pages=[page])
        from contextlib import nullcontext
        with patch('pdfplumber.open',return_value=nullcontext(pdf)):
            if case=='valid':
                result=extract_deposits(db,path,'TEST',1)
                assert result['rows'][3]['values']['2022']=='16297'
                assert result['reconciliation']['2022']['difference']=='0'
            else:
                with pytest.raises(ValueError):extract_deposits(db,path,'TEST',2 if case=='wrong_page' else 1)
        if case!='valid':assert db.db.execute('SELECT COUNT(*) FROM report_tables').fetchone()[0]==0
    finally:db.close()


def test_extractor_rejects_source_changed_since_indexing(store,tmp_path):
    path=tmp_path/'changed.pdf';path.write_bytes(b'changed bytes')
    with pytest.raises(ValueError,match='checksum'):
        extract_deposits(store,path,'BANK_2022',1)


PDF=Path('data/financebench/pdfs/AMERICANEXPRESS_2022_10K.pdf')
@pytest.mark.skipif(not PDF.exists(),reason='Optional local source-PDF integration check; no download in tests')
def test_real_pdf_table_matches_reviewed_values(tmp_path):
    import hashlib
    store=Store(str(tmp_path/'pdf-index.sqlite3'))
    try:
        digest=hashlib.sha256(PDF.read_bytes()).hexdigest()
        store.add('AMERICANEXPRESS_2022_10K','American Express',2022,'',['Test registration'],digest)
        data=extract_deposits(store,PDF,'AMERICANEXPRESS_2022_10K',123)
        expected=parse_deposit_rows(RAW,[2022,2021])
        assert data['totals']==expected['totals']
        assert [r['values'] for r in data['rows']]==[r['values'] for r in expected['rows']]
        assert data['pdf_page']==123 and data['unit']=='millions'
    finally:store.close()
