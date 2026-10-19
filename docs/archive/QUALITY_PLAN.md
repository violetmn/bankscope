# Quality milestones and evidence required

Corpus size and code coverage do not establish answer accuracy. BankScope's
distinguishing workflow is checked historical bank tables, supported by
reproducible retrieval experiments and explicit validation limits.

| Area | Current evidence | Required next evidence |
| --- | --- | --- |
| Retrieval | BM25/dense/rerank diagnostics; document/corpus modes | A larger independent report/question set with an untouched split |
| Repeatability | Local BM25 rankings repeated three times; fingerprints and traces | Re-run semantic methods and across a clean environment |
| Generated answers | Mocked provider, citation/amount failure tests | Human-scored real answers with fixed rubric and bounded API budget |
| Table extraction | One JPM development success; frozen transfer failure | Separate development layouts, then new untouched reports |
| Packaging | Local app, Docker configuration, CI configuration | Actual Docker build/smoke test and successful hosted CI run |
| Presentation | Architecture, reproducible reports, demo/interview guide | Public repository and recorded walkthrough when ready |

## Larger benchmark protocol

Before inspecting outcomes: define report-level development/test splits, group
comparative annual reports from one issuer to avoid overlapping financial facts,
record document checksums, and freeze retrieval settings. Prefer existing public
annotations where source provenance and reuse terms are clear. New questions need
independent verification of answer, evidence page, unit and value year.

Evaluate lexical, dense, hybrid and reranked search on identical inputs in both
scope modes. Preserve failures and skipped counts. Report sample size, per-query
outcomes, retrieval metrics and latency; do not compare scores directly to CUAD
because task, labels and corpus differ. Once inspected or tuned against, a test
set becomes development data.

## Generated-answer rubric

For each supported/unsupported question, independently score factual correctness,
source entailment, citation correctness, number/unit/year alignment and appropriate
abstention. Include conflicting periods, absent information and adversarial source
instructions. Unknown citation IDs and safe refusals are useful controls, but do
not substitute for these judgments. No paid evaluation runs automatically.
