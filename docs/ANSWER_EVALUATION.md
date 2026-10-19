# Answer evaluation and reference review

## Datasets and status

- `data/benchmarks/pilot-v1`: 20 development questions, five source reports,
  1,235 physical pages. Twelve FinanceBench banking/financial-services questions
  have upstream answers and page labels. Eight authored missing-information
  controls test abstention. All references still require independent review.
- `data/benchmarks/finrag-v3`: 100 candidates from FinRAG-QA, spanning 24 banks.
  Forty development questions and sixty reserved-test questions use disjoint
  issuer groups. JPMorgan is forced into development because earlier diagnostics
  already used it. The spreadsheet lacks report URLs and page labels: no retrieval
  or answer-accuracy claims are made for these candidates.
- The v1/v2 drafts were superseded before any evaluation. V1 assigned JPMorgan
  to reserved test; v2 corrected that. Active v3 restricts source publication to
  2023 annual reports so the 100 candidates require 24 reports, rather than a
  larger mix of publication years. Value years remain as annotated.

Raw source data, reference values and PDFs remain local under gitignored `data/`.
No explicit FinRAG-QA reuse license was identified. Cite the upstream repository
and resolve redistribution terms before publishing its annotations.

## Reproduce preparation

Download FinanceBench's American Express and JPMorgan sources with the existing
fetch script. Run from the repository root:

```sh
PYTHONPATH=. python scripts/prepare_pilot.py
python scripts/prepare_finrag.py --source data/finrag/Dataset.xlsx \
  --output data/benchmarks/a-new-finrag-directory
```

FinRAG workbook source:
https://raw.githubusercontent.com/Lsilotto/FinRAG-QA/main/Dataset.xlsx
The import preserves the annotation value as supplied. It does not infer source
currency or label a reference independently verified.

## Larger benchmark source verification

For each candidate, identify the exact report type and publication year from the
issuer's official archive. Record URL, SHA-256, document ID and physical PDF page.
Verify consolidated scope, indicator definition, value year, unit and currency.
A matching number alone is insufficient. Store these in `source_url`, `doc_name`,
`evidence`, `unit`, `reference_review` and `mapping_status`. Do not expose reference
answers to ingestion or generation. Keep all reports from each reserved bank out
of development/tuning; merely indexing their PDFs at final evaluation is allowed.
The active candidate set targets 24 annual reports from 2023. Fourteen
questions across JPMorgan, Citi and Wells Fargo now have automatically checked source
pages; eighty-six still need mapping. All one hundred require independent review.
The Wells Fargo liability table uses parentheses while the annotation stores a
positive magnitude; the independent reviewer must document that sign convention.

## Frozen pilot and cost approval

```sh
python -m bankscope.answer_evaluation preflight \
  --db data/benchmarks/pilot-v1/index.sqlite3 \
  --questions data/benchmarks/pilot-v1/questions.jsonl \
  --output data/benchmarks/pilot-v1/a-new-answer-plan.json
```

Preflight makes no paid calls. It freezes question text and retrieved passages,
records corpus/question fingerprints, and estimates cost with an intentionally
conservative byte-based input allowance plus 600 output tokens per answer. The
plan omits gold answers and expected behavior. Pricing is recorded with its
verification date and official source. A plan is not spending authorization.

After the human approves the run cap, use the same private Terminal where the
key is configured. Do not paste or display the key. Explicit opt-in and the local
attempt cap in `generation.py` still apply:

```sh
export BANKSCOPE_ENABLE_PAID=1
export BANKSCOPE_MAX_CALLS=20
python -m bankscope.answer_evaluation execute \
  --plan data/benchmarks/pilot-v1/answer-plan.json \
  --output data/benchmarks/pilot-v1/real-answer-run \
  --approved-cap-usd 0.10
```

The sample cap above must be approved before executing. A new output directory is
required. No automatic retries; response-validation failures are recorded as outcomes.
Provider errors stop the batch.
Provider authentication/quota failures may stop before all twenty answers exist.
This tool evaluates retrieval plus the existing generator, not the structured
calculation route. Some FinanceBench questions require arithmetic that this
restricted generator deliberately declines. Score that limitation openly.

## Human rubric

Use `reviews.jsonl` produced by the real run. Read the question, upstream reference,
model answer, retrieved passages and original PDF before scoring. Add reviewer
identity, `reference_verified: true` and an explanatory note. A self-review is not
an independent review; record reviewer relationship in the published report.

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| correctness | Wrong or unsupported answer | Partly correct | Material facts correct |
| year_and_units | Wrong institution, period, scale or currency | Ambiguous or incomplete | All requested labels correct |
| citation_support | Missing/irrelevant support | Partial support | Claims supported by cited passages |
| completeness | Requested answer absent | Some requested facts omitted | Request fully addressed |
| abstention | Invents unavailable information or wrongly refuses | Unclear uncertainty | Correct decision to answer or abstain |

Use `n/a` only when the dimension genuinely cannot apply, with a note. A correct
refusal on a missing-information control can earn full correctness, completeness
and abstention credit; citation support can be `n/a` if it makes no report claims.
A refusal on an answerable question is not automatically correct. Blank scores
are never converted into passes. The scoring command requires one reviewed row
for every generated answer and reports the denominator separately per dimension.

```sh
python -m bankscope.answer_evaluation score \
  --answers data/benchmarks/pilot-v1/real-answer-run/answers.jsonl \
  --reviews data/benchmarks/pilot-v1/real-answer-run/reviews.jsonl
```

Do not publish an overall success percentage from incomplete reviews. Report
answerable/abstention subsets, failure examples, partial batches and sample size.
A reviewer should also audit reference annotations; upstream labels are not an
absolute authority when the original PDF contradicts them.

Future evaluation runs retain withheld drafts privately for auditing. They remain
withheld from the normal API. See `reports/validation/PILOT_FAILURE_ANALYSIS.md` for the
original run review and offline scope-check replay; this does not reclassify
the twelve original failures, whose raw drafts were not retained.
