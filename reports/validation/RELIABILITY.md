# Reliability work: 2026-10-19

## Verification

Command:

```sh
.venv/bin/python -m pytest -q --cov=bankscope --cov-branch \
  --cov-report=term-missing --cov-report=json:reports/coverage.json
```

- 106 passing tests (25 before this change); zero paid calls made.
- Statement coverage: 382/472 = 80.93%.
- Branch coverage: 124/152 = 81.58%.
- Combined coverage: 506/624 = 81.09%.
- One third-party warning: Starlette/httpx TestClient deprecation.
- Browser JavaScript syntax checked using Node `--check`.
- GitHub Actions workflow added with an 80% combined coverage floor; no hosted run yet.

## Changes driven by failure cases

1. **Grouped citations:** `[S1, S999]` could hide a nonexistent source from the old
   single-ID parser. Group members are now checked; invalid IDs withhold the answer.
2. **Truncated output:** a provider's incomplete response could contain a citation
   yet still be served as an answer. Incomplete/failed responses are now withheld.
3. **Refusals and malformed payloads:** refusals are distinguished from answers;
   invalid provider response shapes yield curated diagnostics without raw bodies.
4. **Blank questions:** whitespace-only API requests are rejected before retrieval
   or payment. The generator separately checks question lengths.
5. **Money magnitudes:** exact Decimal unit normalization permits equivalent
   millions/billions but warns on unsupported magnitudes and explicit currencies.
   Only cited passages are eligible support. These are lexical/numeric checks, not
   semantic claim verification, and legitimate derived/rounded values may be flagged.
6. **Ledger resources:** explicitly close SQLite connections while preserving atomic
   call reservation. Six concurrent test requests cannot exceed a shared cap of two.
7. **Evaluation validity:** invalid K is rejected even with zero eligible examples;
   duplicate pages cannot inflate recall/NDCG. Metrics are checked by hand.

## Deposit-breakdown regression

The previously reported answer listed components totaling 93.942 billion against
a stated total of 110.239 billion: a 16.297 billion difference. The exact arithmetic
is now a regression test using explicit, same-unit structured inputs. Another case
checks that the interest-bearing/non-interest-bearing components reconcile exactly.
This tests the reconciliation utility; it does **not** establish automatic recognition
of a complete breakdown in free-form model output. Reliable table row/column/year
mapping and automatic use of the structured utility remain unimplemented.

## Test boundaries

No real provider calls or model downloads occur in the suite. A fixture blocks
unexpected urllib requests and removes inherited real credentials. Prompt separation
is tested, but a mock cannot prove real model resistance to prompt injection.
Company/report-year filters are tested; passing a numeric check cannot establish that
a model assigned a value to the correct metric or year. A test explicitly records
that limitation so numerical matching is not mislabeled as full verification.

No retrieval accuracy increase is claimed: the seven-question development result
remains 4/7. Financial question-answering accuracy needs a larger held-out benchmark.
CLI paths and real model preparation are the largest uncovered areas. Frontend
warning code passed syntax validation; no new live paid/browser generation was run.

## Loading the changes locally

Restart the existing server in the same Terminal that holds its private key:
Control+C, then the original uvicorn command. Merely refreshing the browser does
not reload Python code in a server started without `--reload`.
