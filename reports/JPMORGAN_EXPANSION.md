# JPMorgan Chase corpus and table-transfer experiment

Measured locally on 2026-10-19. No paid API calls.

## Corpus and provenance

Three complete reports: American Express 2022 (260 physical pages), JPMorgan
Chase 2023 (364), and JPMorgan Chase 2022 (328). Total: 952 pages, 2,659 passages.
The JPMorgan PDFs come directly from the issuer; URLs and checksums are recorded
in `datasets/bank_reports.json` and `reports/corpus-manifest.json`. Downloads remain
outside Git. PDFium preserves physical page boundaries for the two added reports;
the original American Express index uses pdfplumber. All passages have local BGE
embeddings. Query scope includes company and report year. Comparative figures may
refer to earlier years than the selected report.

## Frozen table adapter

The protocol in `datasets/report_transfer_protocol.json` was recorded before
implementation. Development used the 2023 report only. The adapter fingerprint
in `segment-adapter-freeze.json` was saved before the first 2022 transfer run.

2023 succeeded: the adapter located physical PDF page 143, read the year/unit
headers, separated period-end from average columns, and reconciled all four
columns. Only period-end business-segment rows are served as the structured
answer. These segments are different from deposit-product categories. The source
2023/2022 period-end totals were 2,400,688 / 2,340,179 million report dollars.
The development result is saved in `jpm-development-table.json`.

**First transfer to the 2022 report failed**: financial values did not align with
year headers under the frozen geometry tolerance. The first result is saved in
`jpm-first-transfer-result.json`. Independent source review afterward identified
the deposit table on physical page 120. The adapter was not modified after this
failure. The 2022 report supports normal passage search, but no structured table
is served from that report. A test that expects safe rejection is not a successful
extraction test.

This is one report-format transfer attempt, not an extraction-accuracy benchmark.
The two annual reports overlap in comparative financial periods; they do not
represent independent financial facts. Future adapter work needs separate
training/development documents and a new untouched transfer set.

## Retrieval diagnostics

`datasets/jpm_retrieval_diagnostics.jsonl` contains six authored questions, three
per report. All three questions within each report target the same deposit page.
They were authored after source inspection and are narrow diagnostics, not an
untouched benchmark. Their labels are never ingested into the source index.
Document mode supplies the report identity; corpus mode searches all three reports.
Results measure reference-page retrieval at five passages, not answer accuracy.
The saved `jpm-{strategy}-{mode}.json` files include individual outcomes.

| Method | Document: page in top 5 | MRR | Corpus: page in top 5 | MRR |
| --- | --- | --- | --- | --- |
| bm25 | 6/6 | 0.681 | 6/6 | 0.436 |
| dense | 5/6 | 0.700 | 3/6 | 0.292 |
| rerank | 6/6 | 0.667 | 5/6 | 0.617 |

BM25 finds all six target pages. Reranking improves corpus reciprocal rank but
misses one target page at K=5. No parameters were tuned to these outcomes.

## Verification and limitations

168 tests pass locally; combined statement/branch coverage rounds to 86%.
Tests cover company/year isolation, column geometry and reconciliation, source
paths, PDF resource cleanup, incremental embedding batches, and provider failures.
Provider behavior is mocked; optional real-PDF integration tests skip when source
files are absent. Neither coverage nor these retrieval diagnostics establish real
LLM answer accuracy. The UI labels checked tables separately from passage results.
