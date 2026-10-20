"""Page-bounded chunks and a reproducible SQLite FTS5/BM25 baseline."""
import hashlib
import re
import sqlite3
from pathlib import Path


def chunks(text: str, size: int = 260, overlap: int = 45):
    if not 0 <= overlap < size:
        raise ValueError("Require 0 <= overlap < size")
    words = text.split()
    for start in range(0, len(words), size - overlap):
        yield " ".join(words[start:start + size])
        if start + size >= len(words):
            break


class Store:
    def __init__(self, path="data/index.sqlite3"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, company TEXT NOT NULL, year INTEGER NOT NULL,
            url TEXT NOT NULL, sha256 TEXT NOT NULL, pages INTEGER NOT NULL);
          CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(
            text, doc_id UNINDEXED, page UNINDEXED, chunk_id UNINDEXED,
            tokenize='unicode61');
          CREATE TABLE IF NOT EXISTS embeddings (
            chunk_id TEXT PRIMARY KEY, model TEXT NOT NULL,
            text_sha256 TEXT NOT NULL, vector BLOB NOT NULL);
          CREATE TABLE IF NOT EXISTS page_contexts (
            doc_id TEXT NOT NULL, page INTEGER NOT NULL, text TEXT NOT NULL,
            PRIMARY KEY(doc_id, page));
          CREATE TABLE IF NOT EXISTS report_tables (
            doc_id TEXT NOT NULL, table_id TEXT NOT NULL, data TEXT NOT NULL,
            PRIMARY KEY(doc_id, table_id));
        """)

    def close(self):
        self.db.close()

    def add(self, doc_id, company, year, url, pages, digest):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", doc_id):
            raise ValueError("Document ID may contain letters, numbers, dots, hyphens and underscores")
        if not pages or not any(p.strip() for p in pages):
            raise ValueError("No extractable text; scanned PDFs need OCR (not implemented)")
        with self.db:
            self.db.execute("DELETE FROM report_tables WHERE doc_id=?", (doc_id,))
            self.db.execute("DELETE FROM page_contexts WHERE doc_id=?", (doc_id,))
            self.db.execute("DELETE FROM embeddings WHERE chunk_id IN (SELECT chunk_id FROM passages WHERE doc_id=?)", (doc_id,))
            self.db.execute("DELETE FROM passages WHERE doc_id=?", (doc_id,))
            self.db.execute("INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?,?)",
                            (doc_id, company, int(year), url, digest, len(pages)))
            for page, text in enumerate(pages, 1):
                self.db.execute("INSERT INTO page_contexts VALUES(?,?,?)", (doc_id, page, text))
                for index, passage in enumerate(chunks(text)):
                    self.db.execute("INSERT INTO passages VALUES(?,?,?,?)",
                                    (passage, doc_id, page, f"{doc_id}:p{page}:c{index}"))

    def ingest_pdf(self, path, doc_id, company, year, url, extractor='pdfplumber'):
        path = Path(path)
        if extractor == 'pdfium':
            import pypdfium2
            pages = []
            with pypdfium2.PdfDocument(path) as pdf:
                for i in range(len(pdf)):
                    page = pdf[i]
                    try:
                        textpage = page.get_textpage()
                        try:
                            pages.append(textpage.get_text_bounded() or '')
                        finally:
                            textpage.close()
                    finally:
                        page.close()
        elif extractor == 'pdfplumber':
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                pages = [p.extract_text(layout=False) or "" for p in pdf.pages]
        else:
            raise ValueError('Unknown PDF extractor')
        self.add(doc_id, company, year, url, pages, hashlib.sha256(path.read_bytes()).hexdigest())
        return {"document": doc_id, "pages": len(pages), 'extractor': extractor,
                "empty_pages": sum(not p.strip() for p in pages)}

    def documents(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM documents ORDER BY company, year")]

    def search(self, question, k=5, company=None, year=None, doc_id=None, strategy="bm25"):
        if not 1 <= k <= 20:
            raise ValueError("k must be between 1 and 20")
        if strategy not in {"bm25", "dense", "hybrid", "rerank", "focused", "financial"}:
            raise ValueError("Unknown retrieval strategy")
        if strategy == "financial":
            from bankscope.financial_retrieval import search
            return search(self, question, k, company, year, doc_id)
        if strategy == "focused":
            from bankscope.focused_retrieval import search
            return search(self, question, k, company, year, doc_id)
        if strategy != "bm25":
            from bankscope.semantic import semantic_search
            return semantic_search(self, question, k, company, year, doc_id, strategy)
        # Quote tokens, never interpolate user text into FTS syntax or SQL.
        stop = {"the", "a", "an", "is", "was", "were", "what", "how", "of", "in", "for", "and", "to", "did", "does", "its"}
        tokens = list(dict.fromkeys(t.lower() for t in re.findall(r"\w+", question)
                                   if t.lower() not in stop))[:50]
        if not tokens:
            return []
        match = " OR ".join('"' + t + '"' for t in tokens)
        filters, args = [], [match]
        for column, value in [("company", company), ("year", year), ("id", doc_id)]:
            if value is not None:
                filters.append(f"d.{column} = ?")
                args.append(value)
        where = " AND " + " AND ".join(filters) if filters else ""
        rows = self.db.execute("""SELECT passages.text, passages.doc_id, passages.page,
                passages.chunk_id, d.company, d.year, d.url, bm25(passages) AS rank
            FROM passages JOIN documents d ON d.id=passages.doc_id
            WHERE passages MATCH ?""" + where + " ORDER BY rank, chunk_id LIMIT ?", (*args, k))
        out = []
        for row in rows:
            hit = dict(row)
            hit["page"] = int(hit["page"])
            hit["citation"] = f"[{hit['doc_id']}, PDF page {hit['page']}]"
            hit["source_url"] = hit["url"].split("#")[0] + f"#page={hit['page']}" if hit["url"] else ""
            out.append(hit)
        return out
