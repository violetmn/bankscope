import hashlib
import json
from pathlib import Path
import pytest
from bankscope.segment_tables import parse_segment_words, extract_segment_deposits
from bankscope.store import Store
from bankscope.tables import table_analysis

PAGE_TEXT='The table below summarizes period-end and average deposit balances.'


def words_fixture():
    words=[]
    def word(text,x,y,width=None):
        words.append({'text':text,'x0':x,'x1':x+(width or max(8,len(text)*4)),'top':y})
    word('Average',260,10)
    word('(in',0,20);word('millions)',16,20)
    for x,year in zip([120,180,260,320],['2023','2022','2023','2022']):word(year,x,20,20)
    for index,(label,values) in enumerate([
        ('Consumer & Community Banking',['10','11','12','13']),
        ('Corporate',['2','3','4','5']),
        ('Total Firm',['12','14','16','18']),
    ]):
        y=30+index*10
        word(label,0,y,90)
        for x,value in zip([120,180,260,320],values):word(value,x,y,20)
        if label=='Total Firm':word('$',105,y)
    return words


def test_period_end_and_average_columns_are_not_mixed():
    result=parse_segment_words(words_fixture(),PAGE_TEXT)
    assert result['totals']=={'2023':'12','2022':'14'}
    assert result['average_totals_not_used']=={'2023':'16','2022':'18'}
    assert result['rows'][0]['values']=={'2023':'10','2022':'11'}
    assert result['average_columns_reconcile']


@pytest.mark.parametrize('case',['misaligned','average_heading_missing','missing_number','bad_total','missing_currency','wrong_measure'])
def test_ambiguous_or_nonreconciling_layout_fails_closed(case):
    words=words_fixture();text=PAGE_TEXT
    if case=='misaligned':next(w for w in words if w['text']=='10')['x1']+=20
    elif case=='average_heading_missing':words=[w for w in words if w['text']!='Average']
    elif case=='missing_number':words=[w for w in words if w['text']!='10']
    elif case=='bad_total':next(w for w in words if w['text']=='18')['text']='99'
    elif case=='missing_currency':words=[w for w in words if w['text']!='$']
    elif case=='wrong_measure':text='Average account balances only'
    with pytest.raises(ValueError):parse_segment_words(words,text)


@pytest.fixture
def segment_store(tmp_path):
    store=Store(str(tmp_path/'index.sqlite3'))
    store.add('JPM_TEST','JPMorgan Chase',2023,'https://example.org/report.pdf',['Deposits'],'hash')
    table={**parse_segment_words(words_fixture(),PAGE_TEXT),'doc_id':'JPM_TEST','table_id':'segments',
           'company':'JPMorgan Chase','report_year':2023,'pdf_page':143,
           'category_basis':'business_segment','metric_label':'Period-end deposits','unit':'millions'}
    with store.db:store.db.execute('INSERT INTO report_tables VALUES(?,?,?)',('JPM_TEST','segments',json.dumps(table)))
    yield store
    store.close()


def test_segment_table_can_answer_period_end_question(segment_store):
    result=table_analysis(segment_store,'Show period-end deposits by business segment in 2023','JPMorgan Chase',2023)
    assert result['status']=='calculated_from_table'
    assert result['answer'].startswith('Period-end deposits')


def test_product_type_question_is_not_answered_by_business_segments(segment_store):
    assert table_analysis(segment_store,'Show customer deposits by deposit type','JPMorgan Chase',2023) is None


def test_average_question_is_not_answered_with_period_end_totals(segment_store):
    assert table_analysis(segment_store,'What were average customer deposits in 2023?','JPMorgan Chase',2023) is None


def test_report_year_scope_does_not_substitute_another_report(segment_store):
    assert table_analysis(segment_store,'Show customer deposits in 2022','JPMorgan Chase',2022) is None


def test_extractor_version_matches_pre_transfer_freeze():
    freeze=json.loads(Path('reports/provenance/segment-adapter-freeze.json').read_text())
    assert hashlib.sha256(Path(freeze['file']).read_bytes()).hexdigest()==freeze['sha256']


JPM=Path('data/reports/pdfs')
@pytest.mark.skipif(not (JPM/'JPMORGANCHASE_2023_ANNUAL.pdf').exists(),reason='Local source report not downloaded')
def test_development_pdf_matches_independently_reviewed_values(tmp_path):
    path=JPM/'JPMORGANCHASE_2023_ANNUAL.pdf';store=Store(str(tmp_path/'dev.sqlite3'))
    try:
        store.add('DEV','JPMorgan Chase',2023,'',['Registration'],hashlib.sha256(path.read_bytes()).hexdigest())
        result=extract_segment_deposits(store,path,'DEV',143)
        assert result['totals']=={'2023':'2400688','2022':'2340179'}
        assert result['average_totals_not_used']=={'2023':'2359067','2022':'2467915'}
        assert len(result['rows'])==5
    finally:store.close()


@pytest.mark.skipif(not (JPM/'JPMORGANCHASE_2022_ANNUAL.pdf').exists(),reason='Local transfer report not downloaded')
def test_transfer_pdf_rejection_is_preserved_not_relabelled_as_success(tmp_path):
    path=JPM/'JPMORGANCHASE_2022_ANNUAL.pdf';store=Store(str(tmp_path/'transfer.sqlite3'))
    try:
        store.add('TEST','JPMorgan Chase',2022,'',['Registration'],hashlib.sha256(path.read_bytes()).hexdigest())
        with pytest.raises(ValueError,match='align'):
            extract_segment_deposits(store,path,'TEST',120)
        assert store.db.execute('SELECT COUNT(*) FROM report_tables').fetchone()[0]==0
    finally:store.close()
