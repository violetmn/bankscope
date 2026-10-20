# Evaluation

Start here for measured results. Detailed evidence is grouped by purpose.

## Current results

- **Software reliability:** 200 tests pass locally, approximately 85% combined
  coverage. Provider behavior is mocked in tests; coverage is not answer accuracy.
- **Retrieval:** on twelve inspected development questions across five complete
  reports, standard reranking finds 4/12 reference pages within a known report and
  2/12 across the corpus. The optional focused method finds 8/12 in both modes.
- **Regression:** focused retrieval loses one prior deposit hit while gaining
  another. It is slower and remains opt-in; the default has not changed.
- **AI answers:** twenty real-provider calls produced eight cited drafts and twelve
  withheld citation-validation outcomes. These are not correctness scores.
  Independent human scoring remains pending.
- **Table transfer:** JPMorgan 2023 extraction reconciles; the frozen adapter rejects
  the 2022 layout. Safe rejection is not successful extraction.
- **Larger benchmark:** 100 candidates, with 40 development and 60 reserved-test
  questions across disjoint bank groups. Source mapping and independent review are
  incomplete; no final-test score is claimed.

## Read the findings

| Report | Purpose |
| --- | --- |
| [Retrieval audit](validation/RETRIEVAL_MISS_AUDIT.md) | Miss analysis, before/after results, and rollout decision |
| [AI-answer pilot review](validation/PILOT_FAILURE_ANALYSIS.md) | Failure examples and no-cost fixes |
| [Reliability](validation/RELIABILITY.md) | Test coverage and validation limits |
| [Checked deposit table](validation/DEPOSIT_TABLE.md) | Arithmetic, categories, and source checks |
| [Report-transfer experiment](validation/JPMORGAN_EXPANSION.md) | Frozen adapter protocol and failed transfer |
| [Benchmark status](validation/BENCHMARK_STATUS.md) | Preparation completed and work remaining |

## Reproduction records

- [Experiments](experiments/): per-query metrics, retrieved-page traces and comparisons.
- [Provenance](provenance/): corpus manifests, checksums and adapter fingerprint.
- [Archived development results](archive/): early baselines and milestone notes.

Historical reports describe their own run dates and corpus sizes. They are retained
for reproducibility and are not substitutes for the current summary. The benchmark
annotations, downloaded PDFs, provider answers, and usage ledgers remain local.

## Canadian-bank expansion

The main corpus now contains nine reports and 2,315 pages. Six numerical development
questions exposed selected-reference-page misses (0/6 Hit@5 for BM25 and reranking).
See the [expansion checks and limitations](validation/CANADIAN_EXPANSION.md),
[corpus snapshot](provenance/canadian-expansion-manifest.json), and
[retrieval run](experiments/canadian-expansion/comparison.md).
