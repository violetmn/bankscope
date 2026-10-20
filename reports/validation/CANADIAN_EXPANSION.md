# Canadian-bank corpus expansion

Completed locally on 2026-10-20. Six official publisher annual reports were added
to the main application index. PDFs, model weights, local databases, and the
pre-expansion backup remain excluded from Git.

| Publisher | Fiscal year | Physical PDF pages | Empty extracted pages |
| --- | --- | --- | --- |
| Royal Bank of Canada | 2022 | 235 | 0 |
| Royal Bank of Canada | 2023 | 237 | 0 |
| TD | 2022 | 228 | 0 |
| TD | 2023 | 228 | 0 |
| Bank of Montreal | 2022 | 215 | 1 |
| Bank of Montreal | 2023 | 220 | 1 |

Canadian fiscal years end on October 31. This is a historical 2022-2023 corpus,
not the latest reporting period. Values may be CAD millions, CAD billions, or
percentages; reported and adjusted figures are distinct.

## Corpus and integration checks

- Main index: **9 reports, 2,315 physical pages, 7,687 passages and 7,687 BGE vectors**.
- All nine indexed PDF hashes match the local source files.
- All six new bank/year combinations returned passages through the API with
  correct company/year filtering; their local PDF links returned valid PDFs.
- Browser check: RBC 2023 credit-risk search returned five cited passages using
  semantic search and reranking.
- Existing American Express and JPMorgan structured tables match the backup exactly.
- Re-running preparation ingested no unchanged documents and reused all 7,687 vectors.
- Automated suite: **200 passed**; one third-party deprecation warning.
- **No paid generation calls** were made for this expansion or diagnostic run.

Sources, source hashes, passage fingerprint, and extraction metadata are recorded
in the [corpus snapshot](../provenance/canadian-expansion-manifest.json).

## Six-question development diagnostic

One numerical question was authored per new report. The selected reference tables,
year columns, values and units were checked against rendered PDF pages by the
coding agent. The reference values occur on their indexed pages. Questions and
reference answers were not ingested. Independent human review is pending.

| Method | Within the known report: selected-page Hit@5 | Across all nine reports: selected-page Hit@5 |
| --- | --- | --- |
| BM25 | 0/6 | 0/6 |
| Standard reranker | 0/6 | 0/6 |

These misses are retained without changing the diagnostic labels or tuning the
retriever against them. Each question has one selected reference page; equivalent
support elsewhere in the report was not exhaustively labeled. A page miss does
not establish that every retrieved passage is incorrect. Conversely, finding a
related passage does not establish correct row, year, unit, or numerical support.
This small, inspected development set is not a held-out benchmark or an answer
accuracy score. One run was recorded; ranking repeatability was not tested here.

[Questions and reference values](../../datasets/canadian_bank_diagnostics.jsonl)
· [Measured results and per-query traces](../experiments/canadian-expansion/comparison.md)

## Reproduce

After the README's installation and American Express setup:

```sh
python scripts/fetch_bank_reports.py
python scripts/prepare_bank_index.py --embed
python -m bankscope.experiments \
  --questions datasets/canadian_bank_diagnostics.jsonl \
  --strategies bm25 rerank --repeats 1 \
  --output reports/experiments/my-canadian-run
```

The output directory must be new. Original benchmark runs remain tied to their
original corpus snapshots. The Canadian reports currently support evidence
search; no new checked-table adapters or validated generated answers are claimed.
