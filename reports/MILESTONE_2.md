# Milestone 2: research interface and local retrieval experiments

2026-10-16. No paid model calls made.

## Delivered

- Local research workspace at `/`, replacing Swagger as the entry point.
- Company/year filters, sample questions, loading/error/empty states, expandable
  passages and physical-page links to local PDFs. Generated text is shown only when
  an explicitly configured paid model is requested; evidence is labeled separately.
- BGE-small-en-v1.5 embeddings stored alongside source text in SQLite; reingestion
  invalidates embeddings. Query-time model loading uses local files only.
- Dense retrieval, reciprocal-rank fusion, and MiniLM cross-encoder reranking.
- Explicit-scope queries remove redundant entity/period terms. Semantic methods
  show the highest-ranked passage per distinct PDF page.
- Fifteen tests pass, covering retrieval filters, metadata normalization, reindex
  invalidation, ranking, API validation, UI asset serving and paid-call controls.

## Measured development results

Same 260-page report / seven FinanceBench questions. The other 143 questions remain
excluded because their reports are not indexed.

| System | Hit Rate@5 | MRR |
| --- | --- | --- |
| Original BM25 | 1/7 | 0.143 |
| Scoped dense + page diversity | 2/7 | 0.071 |
| Scoped hybrid + page diversity | 1/7 | 0.143 |
| Scoped candidate union + cross-encoder + page diversity | 4/7 | 0.405 |

New result files: `dense-document.json`, `hybrid-document.json`, `rerank-document.json`.
This is an inspected development subset, not a held-out final benchmark. These
methods differ in multiple components; improvements cannot be attributed solely
to the embedding/reranking model. The API defaults to reranking when its weights and
embeddings are prepared. Hybrid is retained as a measured alternative, not assumed
to be better. Numerical reasoning and answer accuracy remain unvalidated.

## Reproduce

```sh
pip install -e '.[dev,semantic]'
bankscope embed
bankscope prepare-reranker
bankscope evaluate --strategy rerank --mode document
uvicorn bankscope.api:app --host 127.0.0.1 --port 8000
```

The first two commands download model weights; subsequent queries use local caches.
Paid generation remains optional and disabled unless configured. Docker has not
been validated for this milestone. Next: more bank documents, a held-out question
set and numerical/table handling; LLM integration needs a privately configured key.
