import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from bankscope.api import app
from bankscope.store import Store
from bankscope.generation import GenerationError


class APITests(unittest.TestCase):
    def test_query_validation_and_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "test.sqlite3")
            store = Store(path)
            store.add("A_2023", "Bank A", 2023, "https://example.org/a.pdf", ["Total assets: 50 million USD."], "hash")
            store.close()
            with patch("bankscope.api.Store", side_effect=lambda: Store(path)):
                client = TestClient(app)
                self.assertEqual(client.get("/health").status_code, 200)
                self.assertEqual(client.get("/").status_code, 200)
                self.assertIn("Understand the numbers", client.get("/").text)
                self.assertEqual(client.get("/assets/app.js").status_code, 200)
                self.assertEqual(client.get("/capabilities").json()["default_strategy"], "bm25")
                self.assertEqual(client.get("/reports/unregistered.pdf").status_code, 404)
                self.assertEqual(client.post("/query", json={"question": "assets", "k": 100}).status_code, 422)
                response = client.post("/query", json={"question": "total assets", "company": "Bank A"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["sources"][0]["page"], 1)
                self.assertEqual(client.get("/documents").json()[0]["company"], "Bank A")
                self.assertEqual(response.json()["strategy"], "bm25")
                stale = client.post("/query", json={"question":"total assets", "strategy":"dense"})
                self.assertEqual(stale.status_code,400)
                with patch('bankscope.api.generate',side_effect=GenerationError('Check API credit.','billing_or_quota',429)):
                    failed = client.post('/query',json={'question':'total assets','generate_answer':True})
                self.assertEqual(failed.status_code,200)
                self.assertTrue(failed.json()['sources'])
                self.assertEqual(failed.json()['generation']['category'],'billing_or_quota')

    def test_prepared_workspace_routes_numeric_search_to_financial_pages(self):
        text='Financial Highlights\n(Millions of dollars)\n2024 2023\nTotal revenue 137 125\nNet income 73 66\nTotal assets 982 933\n'
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'index.sqlite3')
            store=Store(path);store.add('D','Example Bank',2024,'https://example.test/d.pdf',[text],'hash');store.close()
            with patch('bankscope.api.Store',side_effect=lambda:Store(path)),patch('bankscope.api.ready',return_value=True),patch('bankscope.api.reranker_ready',return_value=True):
                client=TestClient(app)
                self.assertEqual(client.get('/capabilities').json()['default_strategy'],'financial')
                result=client.post('/query',json={'question':'What was total revenue?','company':'Example Bank','year':2024,'k':1})
                self.assertEqual(result.status_code,200)
                self.assertEqual(result.json()['strategy'],'financial')
                self.assertEqual(result.json()['sources'][0]['source_kind'],'financial_table_excerpt')
                self.assertNotIn('table_analysis',result.json())
                self.assertNotIn('generation',result.json())
