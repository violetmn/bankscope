import pytest
from bankscope.store import Store
from bankscope.financial_retrieval import intent, table_candidates

PAGE = '''Financial Highlights
(Millions of Canadian dollars, except ratios)
2024 2023
Total revenue 137 125
Net income 73 66
Adjusted net income 79 76
Total deposits 451 420
Total assets 982 933
Net interest income 86 80
Provision for credit losses 19 12
Capital ratios (%)
Common Equity Tier 1 Ratio 12.5 11.5
Return on common equity 13.4 12.8
'''


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path/'index.sqlite3')
    s.add('A','Example Bank',2024,'https://example.test/a.pdf',[PAGE],'sha')
    s.add('B','Other Bank',2024,'https://example.test/b.pdf',[PAGE.replace('137','999')],'sha')
    s.add('OLD','Example Bank',2023,'https://example.test/old.pdf',[PAGE.replace('2024','2022')],'sha')
    yield s
    s.close()


@pytest.mark.parametrize('question,label',[
    ('What was Example Bank total revenue in 2024?','Total revenue 137'),
    ('What was reported net income in 2024?','Net income 73'),
    ('What was adjusted net income in 2024?','Adjusted net income 79'),
    ('What were total deposits in 2024?','Total deposits 451'),
    ('What were total assets in 2024?','Total assets 982'),
    ('What was net interest income in 2024?','Net interest income 86'),
    ('What was provision for credit losses in 2024?','Provision for credit losses 19'),
    ('What was the CET1 ratio in 2024?','Common Equity Tier 1 Ratio 12.5'),
    ('What was return on common equity in 2024?','Return on common equity 13.4'),
])
def test_numerical_rows_preserve_period_units_and_scope(store,question,label):
    hits=store.search(question,strategy='financial',company='Example Bank',year=2024)
    hit=hits[0]
    assert hit['doc_id']=='A'
    assert hit['source_kind']=='financial_table_excerpt'
    assert label in hit['text']
    assert '2024 2023' in hit['text'] and 'Canadian dollars' in hit['text']
    assert hit['citation']=='[A, PDF page 1]'
    assert hit['source_url']=='https://example.test/a.pdf#page=1'
    assert all(h['company']=='Example Bank' and h['year']==2024 for h in hits)


def test_corpus_scope_is_inferred_from_question_not_gold_labels(store):
    hits=store.search('What was Example Bank total revenue in 2024?',strategy='financial',k=1)
    assert hits[0]['doc_id']=='A'


@pytest.mark.parametrize('question',[
    'Explain why net income changed', 'What was average deposits?',
    'Which segment earned most net income?', 'What was net income in Q2 2024?',
    'What was net income and total revenue?', 'How do deposits fund the bank?',
    'What does the report say about credit risk?',
])
def test_specialized_or_unknown_questions_do_not_use_table_rules(question):
    assert intent(question) is None


@pytest.mark.parametrize('text',[
    PAGE.replace('(Millions of Canadian dollars, except ratios)','Units unavailable').replace('Capital ratios (%)','Other measures').replace('Return on common equity 13.4 12.8',''),
    PAGE.replace('2024 2023','Prior periods'),
    PAGE.replace('Financial Highlights','Divisional operating review'),
    PAGE.replace('Total revenue 137 125','Total revenue increased by 137 over the previous year'),
])
def test_insufficient_table_context_does_not_get_preferred(store,text):
    store.add('A','Example Bank',2024,'',[text],'updated')
    assert table_candidates(store,'total revenue',intent('total revenue'),'Example Bank',2024,'A')==[]


def test_reingestion_replaces_page_contexts(store):
    store.add('A','Example Bank',2024,'',['Replacement page'],'updated')
    assert store.db.execute('select text from page_contexts where doc_id=?',('A',)).fetchone()[0]=='Replacement page'
    assert not table_candidates(store,'total revenue',intent('total revenue'),'Example Bank',2024,'A')


def test_no_source_page_context_falls_back_to_existing_search(store):
    store.db.execute('delete from page_contexts')
    actual=store.search('total revenue',strategy='financial',company='Example Bank',year=2024)
    expected=store.search('total revenue',strategy='bm25',company='Example Bank',year=2024)
    assert actual==expected


def test_inline_row_labels_from_pdf_reading_order_are_retrieved(store):
    page=PAGE.replace('Total deposits 451 420','Other balances 77 66 Total deposits 451 420')
    store.add('A','Example Bank',2024,'',[page],'updated')
    hit=store.search('What were total deposits?',strategy='financial',company='Example Bank',year=2024,k=1)[0]
    assert hit['source_kind']=='financial_table_excerpt' and 'Total deposits 451 420' in hit['text']


def test_requested_year_must_be_in_table_period_columns(store):
    store.add('A','Example Bank',2024,'',[PAGE.replace('2024 2023','2022 2021')],'updated')
    assert table_candidates(store,'total revenue',intent('total revenue'),'Example Bank',2024,'A')==[]


def test_proforma_is_not_preferred_as_actual_consolidated_evidence(store):
    store.add('A','Example Bank',2024,'',['Unaudited pro forma\n'+PAGE],'updated')
    assert table_candidates(store,'total revenue',intent('total revenue'),'Example Bank',2024,'A')==[]


def test_heading_at_end_of_pdf_text_and_letter_footnote(store):
    page=PAGE.replace('Financial Highlights\n','').replace('Total assets 982','Total assets(a) 982')+'\nConsolidated balance sheets\n'
    store.add('A','Example Bank',2024,'',[page],'updated')
    hit=store.search('What were total assets?',strategy='financial',company='Example Bank',year=2024,k=1)[0]
    assert hit['source_kind']=='financial_table_excerpt'
    assert 'Consolidated balance sheets' in hit['text'] and 'Total assets(a) 982' in hit['text']


def test_statement_diversity_prevents_two_highlights_pages_hiding_balance_sheet(store):
    store.add('A','Example Bank',2024,'',[PAGE,PAGE,PAGE.replace('Financial Highlights','Consolidated balance sheets')],'updated')
    hits=store.search('What were total assets?',strategy='financial',company='Example Bank',year=2024,k=2)
    assert [h['page'] for h in hits]==[1,3]


def test_company_aliases_and_inferred_scope_apply_to_all_results(store):
    store.add('R','Royal Bank of Canada',2024,'',[PAGE],'updated')
    hits=store.search('What was RBC total revenue in 2024?',strategy='financial')
    assert hits and all(h['company']=='Royal Bank of Canada' and h['year']==2024 for h in hits)


def test_prose_mention_is_not_a_consolidated_statement_heading(store):
    page=PAGE.replace('Financial Highlights','We adjusted our consolidated balance sheets for a change in accounting.')
    store.add('A','Example Bank',2024,'',[page],'updated')
    assert table_candidates(store,'total assets',intent('total assets'),'Example Bank',2024,'A')==[]


def test_reported_income_does_not_match_an_adjusted_only_row(store):
    page=PAGE.replace('Net income 73 66\n','')
    store.add('A','Example Bank',2024,'',[page],'updated')
    assert table_candidates(store,'reported net income',intent('reported net income'),'Example Bank',2024,'A')==[]
    assert table_candidates(store,'adjusted net income',intent('adjusted net income'),'Example Bank',2024,'A')


def test_windows_line_endings_in_extracted_pdf_heading(store):
    store.add('A','Example Bank',2024,'',[PAGE.replace('\n','\r\n')],'updated')
    hit=store.search('total revenue',strategy='financial',company='Example Bank',year=2024,k=1)[0]
    assert hit['source_kind']=='financial_table_excerpt'
