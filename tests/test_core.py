import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bankscope.store import Store, chunks
from bankscope.evaluation import evaluate
from bankscope.generation import generate


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(str(Path(self.temp.name) / "index.sqlite3"))
        self.store.add("BANK_A_2023", "Bank A", 2023, "https://example.org/report.pdf",
                       ["Annual report cover", "Total assets were 850 million USD in 2023. Capital was 70 million USD."], "abc")
        self.store.add("BANK_B_2022", "Bank B", 2022, "https://example.org/b.pdf",
                       ["Total assets were 900 million EUR in 2022."], "def")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_filters_and_citation(self):
        hits = self.store.search("total assets", company="Bank A", year=2023)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["page"], 2)
        self.assertTrue(hits[0]["source_url"].endswith("#page=2"))
        self.assertFalse(self.store.search("assets", year=2021))

    def test_reingest_replaces_and_empty_rejected(self):
        self.store.add("BANK_A_2023", "Bank A", 2023, "", ["replacement capital disclosure"], "new")
        self.assertFalse(self.store.search("assets", company="Bank A"))
        with self.assertRaises(ValueError):
            self.store.add("bad", "Bank C", 2024, "", [""], "")

    def test_fts_escaping(self):
        self.assertIsInstance(self.store.search('assets " OR * NOT )'), list)
        self.assertEqual(self.store.search("the and of"), [])
        with self.assertRaises(ValueError):
            self.store.search("assets", k=0)

    def test_overlap(self):
        result = list(chunks(" ".join(str(n) for n in range(600))))
        self.assertEqual(result[0].split()[-45:], result[1].split()[:45])
        self.assertTrue(all(len(c.split()) <= 260 for c in result))

    def test_evaluation_offsets_missing_docs_and_no_label_leak(self):
        qs = Path(self.temp.name) / "questions.jsonl"
        row = {"financebench_id": "q1", "question": "total assets", "doc_name": "BANK_A_2023",
               "evidence": [{"doc_name": "BANK_A_2023", "evidence_page_num": 1}],
               "answer": "SECRET GOLD ANSWER"}
        qs.write_text(json.dumps(row) + "\n" + json.dumps({**row, "evidence": [{"evidence_doc_name": "MISSING", "evidence_page_num": 0}]}))
        result = evaluate(self.store, qs)
        self.assertEqual(result["evaluated"], 1)
        self.assertEqual(result["hit_rate"], 1)
        self.assertEqual(result["skipped_missing_documents"], 1)
        self.assertFalse(self.store.search("SECRET GOLD ANSWER"))

    def test_paid_disabled(self):
        with patch.dict("os.environ", {}, clear=True), patch("urllib.request.urlopen") as request:
            with self.assertRaises(ValueError):
                generate("assets?", self.store.search("assets"))
            request.assert_not_called()

    def test_mock_generation_and_call_limit(self):
        from io import BytesIO
        ledger = str(Path(self.temp.name) / "usage.sqlite3")
        response = {"id": "mock", "output": [{"content": [{"type": "output_text", "text": "Assets were 850 million USD [S1]."}]}], "usage": {"input_tokens": 100}}
        with patch.dict("os.environ", {"BANKSCOPE_ENABLE_PAID": "1", "OPENAI_API_KEY": "fake-test-key", "BANKSCOPE_MAX_CALLS": "1"}), patch("urllib.request.urlopen", return_value=BytesIO(json.dumps(response).encode())) as request:
            result = generate("assets?", self.store.search("assets", company="Bank A"), ledger)
            self.assertEqual(result["status"], "generated_unverified_claims")
            with self.assertRaises(ValueError):
                generate("assets?", self.store.search("assets"), ledger)
            self.assertEqual(request.call_count, 1)
