# Numerical retrieval: page context and financial rows

The Canadian expansion's six numerical questions originally missed all selected
reference pages with BM25 and standard reranking. Five reference pages ranked
below the dense top-20 candidate cutoff (best relevant chunk ranks 78-346); the
sixth was a reranking miss. Chunk retrieval favored narrative text over compact,
multi-measure tables.

## Change

`financial` retrieval preserves line-level source pages separately from passage
vectors. For supported numerical metrics, it finds a labeled row, a recognizable
financial-highlights or consolidated-statement heading, period columns and units.
It places at most two qualifying pages before ordinary retrieval results, with
statement/highlights diversity. Excerpts retain headings and nearby rows, marking
gaps with `[...]`. They are source text, not parsed or calculated answers.

Rules use question intent and source text, not diagnostic IDs, financial answers
or page numbers. Entity aliases include RBC, TD and BMO. Company/year filters
apply before selection, including unambiguous scope inferred from a question.
Unsupported, quarterly, segment, average and period-end questions retain ordinary
retrieval. Explicit strategy `rerank` preserves the earlier baseline.

The API selects this route when semantic search, reranking and page contexts are
available. Existing indexes can backfill contexts using source-hash checks without
changing passages, vectors or the existing checked deposit tables. New ingestions
preserve source pages automatically.

## Measured results

Selected-reference-page Hit@5 on the nine-report corpus:

| Question set | Earlier reranker: report / corpus | Final financial route: report / corpus |
| --- | --- | --- |
| Original six Canadian development questions | 0/6 / 0/6 | 6/6 / 6/6 |
| Eight additional development checks | 2/8 / 0/8 | 8/8 / 8/8 |
| Existing six JPMorgan diagnostics | 6/6 / 5/6 | 6/6 / 5/6 |

The final combined 14-question run has MRR 0.946 in both modes; all original six
Canadian reference pages rank first. All returned reference-page texts contain
the expected value and requested year. This string-presence check does **not**
validate row/column alignment, numerical entailment, units, calculations or answer
accuracy. The earlier JPMorgan run has identical returned chunk rankings between
the baseline and the financial route, not just equal aggregate scores.

- [Final 14-question run](../experiments/numerical-release-verified/comparison.md)
- [Additional-check baseline and first iteration](../experiments/numerical-additional-checks/comparison.md)
- [JPMorgan regression comparison](../experiments/numerical-jpm-regression/comparison.md)
- [Machine-readable checks and coverage](numerical-retrieval-summary.json)

**236 tests pass; approximately 86% combined statement/branch coverage.** New checks
cover unknown banks, adjusted/reported distinctions, malformed headings, CRLF
line endings, inline rows, period columns, company/year filters, fallback behavior,
page backfill integrity and preserving vectors and checked tables.

## Limits and evaluation status

These are development results. The original six questions were already inspected.
Eight additional checks were authored separately; they also informed subsequent
fixes. They are neither an independent nor a held-out benchmark. Their source
values were reviewed by the coding agent; independent human review is pending.
One reference page is labeled per question; equivalent support elsewhere is not
exhaustively labeled. These small samples do not establish general accuracy.

The final release run was executed once. An earlier six-question iteration had
identical rankings across two repeats. Intermediate runs, including a rejected
heading-parser build, are retained under `reports/experiments/`; the verified run
above identifies the final implementation and source-page fingerprint. Timings
are local observations, not a controlled latency or load benchmark.

There are no new Canadian checked-table adapters, validated arithmetic outputs or
scored real-provider answers. The UI labels table results as unverified excerpts.
No paid AI calls were made. Existing narrative/unsupported-question behavior and
checked-table calculations are preserved.

## Reproduce

```sh
bankscope prepare-page-contexts
mkdir -p tmp
cat datasets/canadian_bank_diagnostics.jsonl datasets/numerical_additional_checks.jsonl > tmp/numerical-checks.jsonl
python -m bankscope.experiments \
  --questions tmp/numerical-checks.jsonl --strategies financial --repeats 1 \
  --output reports/experiments/my-numerical-check
```

Use a new output directory. The context backfill requires matching local source
PDFs. It does not require rebuilding the 7,687 existing vectors.
