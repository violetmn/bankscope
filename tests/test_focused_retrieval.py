import hashlib
from unittest.mock import patch
import numpy as np
import pytest
from bankscope.store import Store
from bankscope.semantic import MODEL
from bankscope.focused_retrieval import resolve_scope,queries

DOCS=[{'id':'JPMORGAN_2022Q2_10Q','company':'JPMorgan','year':2022},
      {'id':'JPMORGAN_2022_10K','company':'JPMorgan','year':2022},
      {'id':'AMEX_2022_10K','company':'American Express','year':2022}]


def test_question_scope_is_not_gold_document_scope():
    assert resolve_scope("Which JPM segment earned most in 2022 Q2?",DOCS)==('JPMorgan',2022,'JPMORGAN_2022Q2_10Q')
    assert resolve_scope('Compare JPM and American Express in 2022',DOCS)==(None,None,None)
    assert resolve_scope('Compare JPM in 2021 and 2022',DOCS)==('JPMorgan',None,None)
    assert resolve_scope('What were assets?',DOCS)==(None,None,None)
    assert resolve_scope('JPM in 2022 Q2',DOCS,'American Express',2021)==('American Express',2021,None)


def test_expansion_does_not_use_answers_or_evidence_pages():
    result=queries("Which of JPM's segments had lowest net revenue in 2022 Q2?",'JPMorgan')
    assert 'JPM' not in result[0]
    assert any('segment results' in q for q in result)
    assert queries('What is revenue? If unavailable, say so.')[0]=='What is revenue'


def test_focused_result_respects_explicit_scope_and_preserves_source(tmp_path):
    store=Store(tmp_path/'index.db')
    try:
        for doc,company in [('A','American Express'),('J','JPMorgan')]:
            store.add(doc,company,2022,'https://example.test/report.pdf',['Segment net revenue 100 million.'],'sha')
        with store.db:
            for r in store.db.execute('select chunk_id,text from passages').fetchall():
                store.db.execute('insert into embeddings values(?,?,?,?)',(r['chunk_id'],MODEL,hashlib.sha256(r['text'].encode()).hexdigest(),np.array([1,0],dtype=np.float32).tobytes()))
        class Encoder:
            def query_embed(self,q):yield np.array([1,0],dtype=np.float32)
        class Reranker:
            def rerank(self,q,docs,**kwargs):return [1.0]*len(docs)
        with patch('bankscope.focused_retrieval.encoder',return_value=Encoder()),patch('bankscope.focused_retrieval.reranker',return_value=Reranker()),patch('bankscope.focused_retrieval.reranker_ready',return_value=True):
            hits=store.search('JPM revenue 2022',strategy='focused')
            assert {h['doc_id'] for h in hits}=={'J'}
            assert hits[0]['citation']=='[J, PDF page 1]'
            assert store.search('JPM revenue 2022',company='American Express',strategy='focused')[0]['doc_id']=='A'
            assert store.search('revenue',company='Missing',strategy='focused')==[]
        store.add('J','JPMorgan',2022,'',['Revised report'],'new')
        with pytest.raises(ValueError,match='prepared'):
            store.search('revenue',strategy='focused')
    finally:store.close()
