# Retrieval miss audit — development pilot

The original reranked known-document run retrieved a reference page for 4/12
answerable questions. All twelve upstream labels remain in the primary metric;
none were removed because they were difficult. The eight missing-information
controls are not page-retrieval examples.

## Eight misses

| ID suffix | Reference physical page | Best dense chunk rank | Reference in lexical top 20? | Failure stage |
| --- | --- | --- | --- | --- |
| 00723 | 96 | 316 | No | Candidate recall |
| 00720 | 96 | 94 | No | Candidate recall |
| 01351 | 44 | 39 | No | Candidate recall |
| 01981 | 45 | 56 | Yes, rank 20 | Reranking |
| 00299 | 19 | 31 | No | Candidate recall |
| 02119 | 6 | 89 | No | Candidate recall |
| 00206 | 3 | 450 | No | Candidate recall |
| 00394 | 21 | 19 | No | Reranking |

Dense ranks count chunks, not distinct pages. The baseline candidate union uses
up to twenty dense chunks and twenty lexical chunks. Multiple chunks from the
same page can therefore consume candidate capacity before final page diversity.
All eight reference pages have extracted text in the index. Re-extracting PDFs
or rebuilding every embedding was not justified by this audit.

## Label and task limitations

The two American Express margin questions cite an income statement that does not
explicitly state that operating/gross margin is inapplicable. The JPMorgan margin
question cites a business-overview page rather than an explicit discussion of
margin applicability. Their relevance judgments need independent review. A
retriever can find those pages without establishing the expected conclusion.

The liquidation question's reference relies on tangible book value per share.
Retrieving a segment assets/equity table can produce plausible numbers with the
wrong consolidated scope. Retrieval gains do not verify that a calculation or
bankruptcy interpretation is valid.

## Focused retrieval variant

The new optional `focused` strategy is an inspected-development experiment:

- Question-derived company aliases and explicit periods can scope a corpus search.
  These are inferred from the question and corpus metadata, never reference IDs.
  Ambiguous multi-company or multi-year questions do not get forced to one entity
  or period. Explicit caller filters take precedence.
- Short financial query variants reduce instruction boilerplate and expand common
  report terminology for segments, taxes, margins, retention and shareholder value.
- Each dense query contributes twenty distinct source pages before reranking.
- The union is capped at one hundred passages and reranked with the existing local
  MiniLM model. Final results still use distinct physical pages.

No answer values, reference pages or question IDs appear in the retrieval code.
The financial query rules were motivated by this pilot and are consequently
**development tuning**, not evidence of held-out generalization. This compares
complete retrieval systems; it is not an isolated model ablation. Candidate count
and automatically inferred scope differ from the baseline.

The default API strategy remains the original reranker until the measured
comparison and deposit regression check justify a change. Reproduction:

```sh
python -m bankscope.experiments \
  --db data/benchmarks/pilot-v1/index.sqlite3 \
  --questions data/benchmarks/pilot-v1/questions.jsonl \
  --strategies focused --repeats 1 --output reports/experiments/a-new-focused-run
```

Detailed original miss records are in `pilot-retrieval-misses.json`. Raw page text
and private development annotations stay in gitignored `data/`. No paid calls.

Promotion check for this milestone: improve the pilot without reducing Hit@5 in
either scope mode, and lose no reference-page hits on the earlier six-question
deposit diagnostic in either scope mode. Report latency alongside recall. A
failed check leaves the new strategy optional; it does not justify silently
changing the default or discarding a failure. This is a development check only.

## Measured result

| Method | Known report Hit@5 | Corpus Hit@5 | Known report MRR | Corpus MRR |
| --- | --- | --- | --- | --- |
| Original reranker | 4/12 | 2/12 | 0.236 | 0.062 |
| Focused variant | 8/12 | 8/12 | 0.431 | 0.431 |

The focused variant recovers four of the eight original known-document misses:
01351 (tax rate), 01981 (retention), 00299 (segment revenue) and 00394 (segment
income). It loses none of the original pilot hits. The three margin-applicability
questions and the liquidation/tangible-book-value question remain misses. Primary
metrics keep all twelve original questions, including ambiguous references.

The new corpus mode benefits from identifying explicit entity/period information
in the question. It is not an equivalent comparison of cross-encoder weights
alone. No gold document identity is supplied to corpus mode.

### Regression check and rollout decision

On the earlier six-question deposit diagnostic, total Hit@5 stays at 6/6 in
known-document mode and 5/6 in corpus mode. However, corpus mode loses the prior
hit `jpm-dev-period-end` and gains `jpm-dev-average`. Equal totals hide a real
per-question regression. MRR also declines: 0.667 to 0.644 within a report and
0.617 to 0.492 in corpus mode.

The promotion check therefore **fails**. The original reranker remains the
API default. The new `focused` strategy is explicitly optional through the API,
CLI and experiment runner. No repeated tuning was performed to erase this
regression. The saved pilot and regression runs use single repetitions, so
repeatability is unmeasured.

Observed focused median query times were 7.7 seconds within a pilot report and
10.5 seconds across the pilot corpus. Two local evaluation processes overlapped;
these timings include startup and contention and are not a controlled production
latency comparison. The larger candidate pool adds inference work.

### Reproduce or try the optional strategy

```sh
bankscope --db data/benchmarks/pilot-v1/index.sqlite3 ask \
  "Which of JPM's business segments had the lowest net revenue in 2021 Q1?" \
  --strategy focused
```

The API accepts `"strategy": "focused"`; generation remains opt-in separately.
No provider calls were needed for the audit, experiments or tests. Complete
settings, implementation fingerprints and per-question traces:

- `experiments/banking-pilot-focused/run.json`
- `experiments/jpm-focused-regression/run.json`

Tests: 200 passing, approximately 85% combined statement/branch coverage. These
verify scope precedence, ambiguous multi-company/year queries, citation paths,
stale-index rejection and the existing reliability contracts. Code coverage and
development Hit@5 are not generated-answer accuracy or held-out bank performance.
