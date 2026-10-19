# BankScope

Financial report research with page citations and reproducible retrieval evaluation.

**Status: local research prototype with analyst interface and retrieval experiments.** Search requires no API key. Optional
A 20-call real-provider pilot is recorded alongside offline mocked-provider tests;
independent human answer scoring remains pending.
This is not yet a validated banking analyst product.

## Implemented

- Digital PDF extraction with pdfplumber or PDFium; word chunks never cross pages.
- SQLite FTS5 / BM25, optional local BGE embeddings, reciprocal-rank hybrid search,
  and MiniLM cross-encoder reranking, filtered by company, document and report year.
- Physical PDF page citations and links to sources.
- FinanceBench download with labels separated from searchable source PDFs.
- Page-level Hit Rate@K, MRR, recall and NDCG in document or corpus mode.
- A responsive question-and-evidence workspace at `/`; FastAPI API and CLI.
- Optional GPT-4o mini generation, explicitly enabled, with persistent local call cap.

## Setup

Python 3.11 or later:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,semantic]'
python -m pytest
# Include statement/branch coverage (no paid calls):
python -m pytest --cov=bankscope --cov-branch --cov-report=term-missing
```

## Real data

```sh
python scripts/fetch_financebench.py --company 'American Express' --max-docs 1
```

The downloaded sample can be ingested with:

```sh
bankscope ingest data/financebench/pdfs/AMERICANEXPRESS_2022_10K.pdf \
  --id AMERICANEXPRESS_2022_10K --company 'American Express' --year 2022 \
  --url https://raw.githubusercontent.com/patronus-ai/financebench/main/pdfs/AMERICANEXPRESS_2022_10K.pdf
bankscope embed
bankscope prepare-reranker
bankscope ask 'What were total revenues?' --company 'American Express' --year 2022 --strategy rerank
bankscope evaluate --mode document
bankscope evaluate --mode corpus
uvicorn bankscope.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/ to use the research workspace. The developer API remains at `/docs`.
Model preparation downloads free model weights into `data/models`; inference thereafter
uses cached weights locally. Queries do not download models. Rebuild embeddings after
ingestion: reingestion invalidates vectors. The API automatically uses reranking when
prepared, dense search when only embeddings are ready, or BM25 otherwise. CLI strategy
selection stays explicit. Base installation (`pip install -e .`) supports BM25 only.
FinanceBench is a corporate financial benchmark, not a bank-only corpus. The local corpus now includes American
Express 2022 and JPMorgan Chase 2022/2023: three full reports, 952 physical pages
and 2,659 passages. See `reports/corpus-manifest.json` for source checksums.
Pass a commit SHA with `--revision` for reproducibility; PDF checksums are recorded.
Downloaded labels and PDFs stay gitignored. Source reports and annotations retain
upstream terms; public availability does not imply unrestricted redistribution.

## Optional paid generation

Ingestion, search, tests and retrieval evaluation make no paid API calls.
Set OPENAI_API_KEY privately in your shell, then explicitly enable:

```sh
export BANKSCOPE_ENABLE_PAID=1
export BANKSCOPE_MAX_CALLS=20
bankscope ask 'What were total revenues?' --company 'American Express' --year 2022 --strategy rerank --generate
```

Never paste keys into chat or commit them. `.env.example` is a template; local `.env` is automatically loaded by the API
and command entry points. Explicitly exported variables take precedence. API requests can set `generate_answer` to true.
The model is fixed to `gpt-4o-mini`, output capped at 600 tokens, and context at
10 chunks through the API / 5 through the CLI. No automatic retries.
`data/usage.sqlite3` counts attempts atomically (including failures) and stores
provider usage, never keys or prompts. This is a **local request-count cap, not a
dollar or account-wide spending limit**. Separate installations have separate ledgers.
Source-ID checks do not verify that claims are actually supported; review sources.
Interrupted answers and unknown citation IDs (including grouped citations) are
withheld. Explicit monetary magnitudes are compared with the **cited** excerpts;
unmatched amounts produce a visible warning, not a declaration of correctness.
This check does not verify table row/year alignment or whether a breakdown is complete.

## Reliability tests

Latest local run (2026-10-19): **200 passing tests**, approximately **85% combined coverage**.
Optional integration tests check downloaded source PDFs; they skip in a clean CI
checkout. Tests block unexpected provider network
calls and remove real API credentials from their environment. Paid-provider behavior
is mocked; this does not establish real LLM answer accuracy or injection resistance.

Tests cover scope isolation, citation grouping, interrupted/refused/malformed
responses, monetary scales/currencies, the incomplete deposit-breakdown arithmetic,
concurrent call-cap enforcement, credential redaction, and hand-calculated retrieval
metrics. They exposed and fixed validation gaps and unclosed ledger connections.
The structured reconciliation helper is **not automatically applied to generated
prose**. The focused deposit-table workflow below does use it on extracted rows.
General financial-table extraction remains future work.

`.github/workflows/tests.yml` is configured to run offline tests and require 80%
combined coverage after dependency installation on GitHub push/PR. It has not run
on GitHub yet. CLI and model-download preparation paths have limited test coverage.
See `reports/RELIABILITY.md` for scope and measured limits.

## Checked customer-deposit table workflow

After ingesting the American Express report, run:

```sh
bankscope extract-deposits data/financebench/pdfs/AMERICANEXPRESS_2022_10K.pdf \
  --id AMERICANEXPRESS_2022_10K --page 123
```

The extractor reads the original PDF table cells and adjacent year/unit heading.
It records all six deposit categories, both year columns, source page and PDF
checksum. Each year's categories must reconcile exactly to the reported total or
extraction fails. Reingesting a PDF invalidates its stored structured tables.

Try these questions in the workspace:

- `Break down customer deposits in 2022`
- `How much did customer deposits increase from 2021 to 2022?`
- `What were customer deposits in 2025?`

Supported questions return a table and deterministic Decimal calculations without
a paid LLM request, even when generation is enabled. Unsupported periods are stated
explicitly. This is a scoped two-column deposit-type extractor and narrow question
router, **not** a general financial-table agent. Ambiguous institutions, geographies,
and causal questions fall back to the normal research pipeline. The dollar symbol
is preserved; the workflow does not infer currency codes or perform FX conversions.
See `reports/DEPOSIT_TABLE.md` for evidence and limitations.

## JPMorgan Chase expansion

The report library now supports company/year selection and labels whether a checked
structured table is available. The 2023 JPMorgan report supports period-end deposits
by business segment, with period-end and average columns validated separately.
Segment categories differ from the American Express deposit-product categories.

```sh
python scripts/fetch_bank_reports.py
bankscope ingest data/reports/pdfs/JPMORGANCHASE_2023_ANNUAL.pdf \
  --id JPMORGANCHASE_2023_ANNUAL --company 'JPMorgan Chase' --year 2023 \
  --extractor pdfium \
  --url https://www.jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/investor-relations/documents/annualreport-2023.pdf
bankscope ingest data/reports/pdfs/JPMORGANCHASE_2022_ANNUAL.pdf \
  --id JPMORGANCHASE_2022_ANNUAL --company 'JPMorgan Chase' --year 2022 \
  --extractor pdfium \
  --url https://www.jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/investor-relations/documents/annualreport-2022.pdf
bankscope extract-segment-deposits data/reports/pdfs/JPMORGANCHASE_2023_ANNUAL.pdf \
  --id JPMORGANCHASE_2023_ANNUAL
bankscope embed
```

Try `Show period-end deposits by business segment in 2023` with JPMorgan Chase
and report year 2023 selected. Calculations use extracted rows without a paid call.
Embedding preparation reuses unchanged vectors and commits new vectors in batches.

The adapter was developed on 2023 and frozen before a first transfer attempt on
2022. **That transfer failed the column-alignment check.** No 2022 structured table
is served; its full report remains searchable. The frozen adapter was not retuned
on this failure. Passing a rejection test demonstrates safe handling, not extraction
success. These two reports also share comparative years and are not independent
financial evidence. See `reports/JPMORGAN_EXPANSION.md` for the protocol and results.

## Evaluation and limitations

Initial measured baseline: **Hit Rate@5 = 1/7 (14.3%)**, MRR = 0.143, on seven
questions associated with the one indexed 260-page report; 143 other examples skipped.
Document and corpus mode coincide with only one document. This small diagnostic
subset does not establish general performance. Results and corpus checksum are in
`reports/baseline-document.json` and `reports/baseline-corpus.json`. No generated-answer
accuracy has been measured. The baseline is weak and should not be presented as
production quality. These seven examples are now development diagnostics, not an
untouched test set.

Current development comparison, same report and seven questions:

| Method | Reference page in top 5 | MRR |
| --- | --- | --- |
| Original BM25 | 1/7 (14.3%) | 0.143 |
| Scoped dense + distinct pages | 2/7 (28.6%) | 0.071 |
| Scoped hybrid + distinct pages | 1/7 (14.3%) | 0.143 |
| Scoped candidates + cross-encoder + distinct pages | 4/7 (57.1%) | 0.405 |

These are system comparisons, not isolated model ablations: the newer methods remove
redundant company/report-year terms when scope is explicit and diversify pages.
Reranking scores the union of up to 20 dense and 20 lexical candidates before returning
the best passage on each of five distinct pages. Seven questions are too few to claim
general accuracy; these examples were inspected during development. See `reports/*-document.json`.
The interface labels excerpts as evidence to review, never a verified generated answer.

Gold answers/evidence never enter the index or generation prompt. Only examples
whose evidence documents are indexed are evaluated; skipped counts are reported.
Document mode supplies known document identity and is easier than corpus mode.
Metrics measure page retrieval, not answer accuracy or exact evidence support.
Use held-out examples for final results, not repeated tuning to the test set.
Physical PDF pages may differ from printed labels. Tables may lose reading order.
Scanned pages require OCR (not implemented). Report-year filters do not identify
the year of every comparative figure. There is no production authentication; run locally.
Docker configuration is supplied but must be built/tested before deployment.

## Next milestones

1. Expand the frozen table adapter using a separate development set.
2. Add more banks/Pillar 3 reports and FinRAG-QA, with source mapping and reuse review.
3. Expand retrieval comparison to a larger, untouched set of documents/questions.
4. Add table extraction, verified currency/unit-aware calculations, abstention and answer evaluation.
5. Add experiment tracking and deployment hardening.

## Sources

- [FinanceBench](https://github.com/patronus-ai/financebench), Islam et al. (2023).
- [FinRAG-QA](https://github.com/Lsilotto/FinRAG-QA), planned banking benchmark.
- [OpenAI documentation](https://developers.openai.com/api/docs/guides/text)
  and [model pricing](https://developers.openai.com/api/docs/models/gpt-4o-mini).

## Reproducible experiment runs

```sh
python -m bankscope.experiments \
  --questions datasets/jpm_retrieval_diagnostics.jsonl \
  --strategies bm25 dense hybrid rerank --repeats 2 \
  --output reports/experiments/my-new-run
```

Each new run directory records data/corpus fingerprints, settings, per-query
retrieved pages and chunk IDs, metrics, elapsed query times and repeatability,
plus a Markdown comparison. Existing run directories are never overwritten.
This is local file-based experiment tracking; it does not use MLflow.
A measured three-repeat lexical run is in
[reports/experiments/jpm-bm25-repeatability/comparison.md](reports/experiments/jpm-bm25-repeatability/comparison.md).

- [Architecture and design choices](docs/ARCHITECTURE.md)
- [Demo and interview guide](docs/DEMO_AND_INTERVIEW.md)
- [Quality milestones and evaluation protocol](docs/QUALITY_PLAN.md)

## Banking answer-evaluation pilot

A separate development index contains five full reports (1,235 physical pages),
twelve FinanceBench banking questions and eight authored missing-information
controls. The initial BM25 baseline retrieves the reference page for 2/12
answerable questions at K=5. The controls have no reference page and are excluded
from retrieval metrics, not counted as retrieval successes.

A larger FinRAG-QA candidate set contains 100 questions across 24 banks, with
40 development and 60 reserved-test questions in disjoint issuer groups. It is
**not ready for evaluation**: report URLs, physical evidence pages and independent
reference review are pending. Its annotations remain local pending reuse review.

The answer-evaluation tool freezes retrieved contexts without gold labels,
estimates provider cost before execution, and produces explicit human-review
forms. No real-answer accuracy score exists yet. See
[the evaluation guide](docs/ANSWER_EVALUATION.md) for commands, rubric and status.

Pilot failure review and no-cost fixes: [reports/PILOT_FAILURE_ANALYSIS.md](reports/PILOT_FAILURE_ANALYSIS.md).
The original 20 real calls are preserved; no paid rerun has been performed.

## Retrieval miss analysis

The eight missed development questions are audited by candidate recall versus
reranking in [reports/RETRIEVAL_MISS_AUDIT.md](reports/RETRIEVAL_MISS_AUDIT.md).
An optional `focused` strategy tests question-derived entity/period scope,
financial query expansion and more distinct candidate pages. It uses no reference
answers or evidence-page labels at query time. On the 12-question development pilot, reference-page Hit@5 improves from 4/12
to 8/12 within a known report, and 2/12 to 8/12 across the corpus. One earlier
deposit question regresses despite unchanged aggregate hits, so the original
reranker remains the default. Use `--strategy focused` to try the experimental
variant; it is slower and has no held-out generalization claim.
