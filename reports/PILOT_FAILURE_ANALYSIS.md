# Pilot review and fixes — 2026-10-19

## Evidence and review status

The original twenty-call pilot remains unchanged in the local output directory.
It produced eight cited drafts and twelve withheld citation-validation outcomes.
These are pipeline statuses, not correctness scores. The preliminary review below was automated using saved references and retrieved
passages. It is not an independent human review, and no human scorecards were
populated automatically.

The twelve withheld original drafts were not retained. Their underlying answers
cannot be reconstructed from provider token usage. Some may have been reasonable
uncited refusals; it would be incorrect to call all twelve hallucinations, or to
retroactively count them as successful abstentions.

## Review findings on the eight served drafts

| Pilot ID suffix | Agent finding | Implication |
| --- | --- | --- |
| 00476 | Broadly agrees with reference on absence of registered debt securities; phrasing relies on disclosure absence | Independent source check still required |
| 01028 | Country list substitutes for the requested primary operating regions in the reference | Correct entities alone do not establish completeness |
| 00720 | General margin rationale is not established by the cited retrieved excerpts | Matching the reference conclusion does not establish citation support |
| 01981 | Draft declines a definitive answer although upstream reference says yes | Retrieval insufficiency can cause an answerability failure |
| 02119 | Draft uses a segment balance-sheet figure as company-wide assets/equity | Numeric magnitude checks do not establish consolidated scope |
| 00206 | Broadly matches the upstream gross-margin conclusion, but cited excerpts do not establish the full rationale | Domain knowledge must not be presented as document-grounded evidence |
| 02049 | Direction of VaR change agrees with reference and the relevant retrieved discussion | Promising supported case, pending independent review |
| abstention-05 | Gives an old capital ratio for a real-time request and blurs capital approaches | A valid citation can still support the wrong temporal or metric scope |

## Changes made without additional paid calls

1. Narrow pre-generation checks decline explicit live financial figures, private
   customer credentials/account data, and certain future fiscal-year actuals.
   Forecasts, maturity schedules and aggregate private-banking questions are
   excluded from blanket rejection. These checks are lexical, not a semantic
   answerability classifier.
2. Offline replay identifies all eight inspected missing-information controls and
   flags none of the twelve answerable pilot questions. This is an inspected
   development result, not held-out accuracy. Broader paraphrases can evade it.
3. Citation failures distinguish empty output, absent citations and unknown IDs.
   Ordinary uncited factual prose remains withheld; the validator was not relaxed
   to accept arbitrary uncited answers.
4. Future evaluation runs explicitly retain withheld draft text in private local
   audit output. The normal API never returns that audit field. This enables
   review of valid refusals versus unsupported uncited answers in a future run.
5. Single-run semantic experiments now show repeatability as unmeasured rather
   than the trivial value true. Saved retrieval outcomes and timings are unchanged.

## Retrieval comparison on twelve answerable pilot questions

Eight authored missing-information controls have no reference page and are
excluded from retrieval denominators. Five complete reports are indexed.

| Method | Known report: Hit@5 | Corpus: Hit@5 | Corpus MRR |
| --- | --- | --- | --- |
| BM25 | 2/12 | 2/12 | 0.167 |
| Dense | 4/12 | 2/12 | 0.058 |
| Hybrid | 2/12 | 2/12 | 0.125 |
| Rerank | 4/12 | 2/12 | 0.062 |

BM25 was repeated twice with identical rankings. Semantic methods ran once, so
repeatability was not measured. Reranking improves known-document page recall
but does not improve corpus recall on this small development pilot. The old
six-question diagnostic concentrated on two deposit pages and was easier; its
scores should not be substituted for these results.

## Remaining work

- Independent verification and scoring of the original pilot references/answers.
- Broader development data for evidence completeness, consolidated scope and
  table column alignment; the new input checks do not solve these problems.
- A separately approved real-provider rerun after choosing a revised pipeline.
  The original approval covered one twenty-call pilot, not unlimited reruns.
- Complete mapping for the larger FinRAG candidate set: fourteen questions across
  three development issuers have automatically checked source pages; eighty-six remain
  unmapped. All one hundred still require independent review.
