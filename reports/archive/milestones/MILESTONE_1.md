# Milestone 1: local retrieval baseline

Completed 2026-10-16. No paid API requests made.

## Verified

- FinanceBench: 150 public question records downloaded separately from the index.
- One full source PDF: AMERICANEXPRESS_2022_10K, 260 physical pages, zero empty extracted pages.
- Source-page rendering inspected for the consolidated balance sheet: physical page 98
  corresponds to printed page 95. Citations explicitly use physical PDF pages.
- Eight automated tests cover retrieval, API behavior, label separation, offsets,
  reingestion and mocked paid-generation controls.
- BM25 baseline retrieves the annotated evidence page in the top five for 1/7 questions.
  Scores are diagnostic, not a held-out final result. 143 missing-document questions skipped.

## Boundaries

The current API returns candidate source passages without needing a key. It does not
yet provide a validated end-to-end RAG answer. The optional generation adapter was
tested with mocks only. Source-ID validation is not semantic claim verification.
BM25 is a transparent reference baseline; dense retrieval and reranking remain next.
Bank-specific corpus assembly, numerical tools, analyst UI, MLflow and deployment
are future milestones. Docker has not been run in this environment.

## Reproduce

Follow README setup, download and ingestion. Run both evaluator modes and tests.
The raw report is gitignored; the metric JSON files include its checksum and URL.
`requirements-lock.txt` captures the tested macOS/Python 3.14 environment; use
pyproject dependencies for other platforms and refresh the lock after validation.
