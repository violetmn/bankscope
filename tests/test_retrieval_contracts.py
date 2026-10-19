import pytest
from bankscope.store import Store, chunks


@pytest.fixture
def store(tmp_path):
    db=Store(str(tmp_path/'index.sqlite3'))
    db.add('A_2022','Bank A',2022,'https://example.org/a.pdf#old',['Cover','Deposits were $10 million.'],'a')
    db.add('A_2023','Bank A',2023,'https://example.org/b.pdf',['Deposits were $20 million.'],'b')
    db.add('B_2023','Bank B',2023,'https://example.org/c.pdf',['Deposits were EUR 30 million.'],'c')
    yield db
    db.close()


@pytest.mark.parametrize('filters,expected',[
    ({'company':'Bank A'},{'A_2022','A_2023'}),
    ({'company':'Bank A','year':2022},{'A_2022'}),
    ({'company':'Bank B','year':2023},{'B_2023'}),
    ({'doc_id':'A_2023'},{'A_2023'}),
    ({'company':'Unknown'},set()),
    ({'year':2025},set()),
    ({'company':"Bank A' OR 1=1 --"},set()),
])
def test_entity_and_period_isolation(store,filters,expected):
    assert {h['doc_id'] for h in store.search('Deposits',**filters)}==expected


def test_citation_fragment_replaces_old_fragment(store):
    hit=store.search('Deposits',doc_id='A_2022')[0]
    assert hit['source_url']=='https://example.org/a.pdf#page=2'


def test_failed_reingestion_preserves_old_document(store):
    with pytest.raises(ValueError):
        store.add('A_2022','Bank A',2022,'',[''],'new')
    assert '$10' in store.search('Deposits',doc_id='A_2022')[0]['text']


@pytest.mark.parametrize('doc_id',['../secret','a/b','a?x=1','a#page=2'])
def test_path_like_document_ids_rejected(store,doc_id):
    with pytest.raises(ValueError):
        store.add(doc_id,'Bank A',2022,'',['Deposits'],'hash')


def test_overlap_never_creates_cross_page_passages(store):
    store.add('PAGES','Bank A',2024,'',['Only first page sentinel','Only second page marker'],'hash')
    hits=store.search('sentinel OR marker',doc_id='PAGES')
    assert len(hits)==2
    assert all(not ('sentinel' in h['text'] and 'marker' in h['text']) for h in hits)


@pytest.mark.parametrize('size,overlap',[(0,0),(10,10),(10,-1),(10,11)])
def test_invalid_chunk_settings_rejected(size,overlap):
    with pytest.raises(ValueError):
        list(chunks('financial report text',size,overlap))
