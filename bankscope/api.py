"""Local API. Ingestion is CLI-only; no arbitrary URL or file-path endpoints."""
import os
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from bankscope.store import Store
from bankscope.generation import generate, GenerationError
from bankscope.semantic import ready, reranker_ready
from bankscope.tables import table_analysis
from bankscope.files import report_path

from bankscope.config import load_private_env

load_private_env()

app = FastAPI(title="BankScope", version="0.2.0", description="Financial report research. Start at / for the workspace, /docs for the API.")
WEB = Path(__file__).parent / "web"
app.mount("/assets", StaticFiles(directory=WEB), name="assets")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(WEB / "index.html")


class Query(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    company: str | None = None
    year: int | None = None
    k: int = Field(default=5, ge=1, le=10)
    generate_answer: bool = False
    strategy: str = Field(default="auto", pattern="^(auto|bm25|dense|hybrid|rerank|focused)$")

    @field_validator("question")
    @classmethod
    def meaningful_question(cls, value):
        value = value.strip()
        if len(value) < 3 or not any(c.isalnum() for c in value):
            raise ValueError("Enter a question containing at least three characters and a letter or number")
        return value


@app.get("/health")
def health():
    return {"status": "ok", "stage": "research-prototype"}


def default_strategy(store):
    if ready(store):
        return "rerank" if reranker_ready() else "dense"
    return "bm25"


@app.get("/capabilities")
def capabilities():
    store = Store()
    try:
        semantic = ready(store)
        return {"semantic_ready": semantic, "default_strategy": default_strategy(store),
                "generation_enabled": os.getenv("BANKSCOPE_ENABLE_PAID") == "1" and bool(os.getenv("OPENAI_API_KEY"))}
    finally:
        store.close()


@app.get("/reports/{doc_id}.pdf", include_in_schema=False)
def report(doc_id: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", doc_id):
        raise HTTPException(404, "Report not found")
    store = Store()
    try:
        registered = any(d["id"] == doc_id for d in store.documents())
    finally:
        store.close()
    path = report_path(doc_id)
    if not registered or path is None:
        raise HTTPException(404, "Local report unavailable")
    return FileResponse(path, media_type="application/pdf")


@app.get("/documents")
def documents():
    store = Store()
    try:
        docs = store.documents()
        for doc in docs:
            doc['structured_table_ready'] = bool(store.db.execute('SELECT 1 FROM report_tables WHERE doc_id=? LIMIT 1',(doc['id'],)).fetchone())
        return docs
    finally:
        store.close()


@app.post("/query")
def query(q: Query):
    store = Store()
    try:
        table_result = table_analysis(store, q.question, q.company, q.year)
        if table_result is not None:
            table = table_result['table']
            return {'mode': 'structured_table', 'strategy': 'validated_table', 'sources': [],
                    'table_analysis': table_result,
                    'note': 'Structured source table and Python calculations; no paid model call.'}
        strategy = default_strategy(store) if q.strategy == "auto" else q.strategy
        hits = store.search(q.question, q.k, q.company, q.year, strategy=strategy)
        for hit in hits:
            path = report_path(hit['doc_id'])
            if path is not None:
                hit["source_url"] = f"/reports/{hit['doc_id']}.pdf#page={hit['page']}"
        result = {"mode": "evidence_search", "sources": hits,
                  "strategy": strategy,
                  "note": "Retrieved passages are candidates, not verified answers."}
        if q.generate_answer:
            try:
                result["generation"] = generate(q.question, hits)
            except GenerationError as exc:
                # Preserve usable local search results when the provider fails.
                result["generation"] = {"status": "error", "answer": str(exc),
                                        "category": exc.category, "provider_http_status": exc.status}
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        # Provider error bodies may contain sensitive details; do not expose them.
        raise HTTPException(502, "Request failed; check local configuration or provider availability.") from exc
    finally:
        store.close()
