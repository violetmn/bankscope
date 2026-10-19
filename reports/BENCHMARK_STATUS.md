# Banking benchmark status — 2026-10-19

## Completed preparation

- A separate development pilot index: five complete public reports, 1,235 physical
  pages, 3,454 passages. It does not alter the app's existing three-report index.
- Twenty pilot questions: twelve FinanceBench annotations from American Express
  and JPMorgan, plus eight authored missing-information controls.
- A frozen BM25 document-scoped generation plan with no reference-answer leakage.
- Conservative estimated pilot cost: US$0.050506 at the recorded GPT-4o-mini rates.
  The user explicitly approved up to US$0.10. The approved run completed after private `.env` loading was added;
  see `pilot-real-answer-summary.json` for token usage and status counts.
- An explicit human-review rubric and a scorer that rejects unreviewed rows.
- One hundred larger FinRAG-QA candidates from twenty-four banks, restricted to
  2023 annual reports. Issuer-disjoint split: forty development, sixty reserved
  test. JPMorgan is development because prior diagnostics already used it.
- Fourteen development references across JPMorgan, Citi and Wells Fargo mapped
  to visually checked original source pages. Eighty-six questions remain unmapped.
  All one hundred still need independent reference review. The candidate set is
  not a completed benchmark and has no accuracy score.

## Initial pilot retrieval baseline

BM25 finds a reference page in the top five for 2/12 answerable questions in both
known-document and corpus modes. Missing-information controls have no reference
pages and are excluded from these retrieval denominators. Two repeats return
identical rankings. This pilot is development data, not a final held-out result.
See `experiments/banking-pilot-bm25/comparison.md` and its per-query JSON trace.

Semantic comparisons completed: dense and rerank find 4/12 reference pages
within a known report, and 2/12 across the corpus. Hybrid finds 2/12 in either
mode. Semantic methods ran once; repeatability is not measured.
See `PILOT_FAILURE_ANALYSIS.md` for the original answer review and no-cost fixes. Do not
infer answer correctness from retrieval or unit-test coverage.

## Pending real-answer evidence

Twenty real provider calls have completed. Independent scoring remains pending.
Inspect `data/benchmarks/pilot-v1/real-answer-run`. Provider
errors and partial batches must remain visible. Answer scoring requires source
review; a generated response is not a verified answer. The review form's blank
scores do not count as successful answers.

## Reproduction and sources

Commands and the complete rubric: `docs/ANSWER_EVALUATION.md`.
Source provenance: `reports/finrag-candidate-manifest.json`, the local pilot
manifest, per-PDF SHA-256 values, and experiment fingerprints. Raw annotations,
reference values, generated answers, usage records and PDFs remain gitignored.
The importer preserves upstream values and does not invent missing source maps.
FinRAG-QA redistribution permission remains to be resolved before publishing
its annotations; the public manifest contains metadata and status only.
