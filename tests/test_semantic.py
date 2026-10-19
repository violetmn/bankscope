import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("Install the semantic extra to run vector tests")
from bankscope.store import Store
from bankscope.semantic import MODEL, ready, fuse, scoped_query, distinct_pages


class FakeEncoder:
    def query_embed(self, text):
        yield np.array([1, 0], dtype=np.float32)


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(str(Path(self.temp.name) / 'index.sqlite3'))
        for doc, company, year, text in [('A', 'Bank A', 2023, 'Client funding grew.'), ('B', 'Bank B', 2022, 'Other deposits declined.')]:
            self.store.add(doc, company, year, 'https://example.org/report.pdf', [text], 'hash')
        with self.store.db:
            for row in self.store.db.execute('SELECT chunk_id,text FROM passages').fetchall():
                vector = [1, 0] if row['chunk_id'].startswith('A:') else [0, 1]
                self.store.db.execute('INSERT INTO embeddings VALUES(?,?,?,?)',
                    (row['chunk_id'], MODEL, hashlib.sha256(row['text'].encode()).hexdigest(), np.array(vector, dtype=np.float32).tobytes()))

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_dense_returns_semantic_match_without_lexical_overlap(self):
        with patch('bankscope.semantic.encoder', return_value=FakeEncoder()):
            result = self.store.search('customer balances', strategy='dense')
        self.assertEqual(result[0]['doc_id'], 'A')
        self.assertEqual(result[0]['similarity'], 1)
        self.assertEqual(result[0]['page'], 1)

    def test_filters_apply_before_dense_ranking(self):
        with patch('bankscope.semantic.encoder', return_value=FakeEncoder()):
            self.assertEqual(self.store.search('funding', company='Bank B', strategy='dense')[0]['doc_id'], 'B')
            self.assertEqual(self.store.search('funding', year=2020, strategy='dense'), [])

    def test_reingestion_invalidates_semantic_index(self):
        self.assertTrue(ready(self.store))
        self.store.add('A', 'Bank A', 2023, '', ['New financial disclosure'], 'new')
        self.assertFalse(ready(self.store))
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.store.search('funding', strategy='dense')

    def test_fusion_deduplicates_chunks_and_rewards_agreement(self):
        a,b,c = ({'chunk_id': k} for k in ['a','b','c'])
        result = fuse([a,b], [b,c], 3)
        self.assertEqual(result[0]['chunk_id'],'b')
        self.assertEqual(len(result),3)

    def test_query_scope_only_removes_explicit_metadata(self):
        query = "What were Bank A's total assets in FY2023?"
        self.assertNotIn('Bank A', scoped_query(query, 'Bank A', 2023))
        self.assertNotIn('FY2023', scoped_query(query, 'Bank A', 2023))
        self.assertEqual(scoped_query(query), query.rstrip('?'))

    def test_page_diversity_keeps_highest_ranked_passage(self):
        hits = [{'doc_id':'A','page':1,'chunk_id':'a'}, {'doc_id':'A','page':1,'chunk_id':'b'}, {'doc_id':'A','page':2,'chunk_id':'c'}]
        self.assertEqual([h['chunk_id'] for h in distinct_pages(hits,2)],['a','c'])

    def test_reranking_uses_scores_and_preserves_filters(self):
        class FakeReranker:
            def rerank(self, query, documents, **kwargs):
                return [float('Other' in text) for text in documents]
        with patch('bankscope.semantic.encoder', return_value=FakeEncoder()), patch('bankscope.semantic.reranker_ready', return_value=True), patch('bankscope.semantic.reranker', return_value=FakeReranker()):
            self.assertEqual(self.store.search('deposits', strategy='rerank')[0]['doc_id'],'B')
            self.assertEqual(self.store.search('deposits', company='Bank A', strategy='rerank')[0]['doc_id'],'A')
