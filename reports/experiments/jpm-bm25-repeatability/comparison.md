# Retrieval experiment

Created: 2026-10-19T20:29:40.567281+00:00

| Method | Scope | Queries | Hit@K | MRR | NDCG@K | Median seconds | Same rankings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bm25 | document | 6 | 1.000 | 0.681 | 0.760 | 0.005 | True |
| bm25 | corpus | 6 | 1.000 | 0.436 | 0.575 | 0.007 | True |

Question SHA-256: `15c2bdb4deabf197e2925283e782ddcfc8e6a759331af76ad23ba92c212f2254`

Passage SHA-256: `7c7d859569de2360ea6e3cba5b228bbb9c76b50d09a86a7c9d13ff110de456df`

- Page retrieval is not answer accuracy.
- Repeatability is measured on this local index and environment only.
- Timing includes first-query model startup; not a production load test.
- Dataset independence and split quality require separate review.
