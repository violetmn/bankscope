# Retrieval experiment

Created: 2026-10-19T21:16:17.523303+00:00

| Method | Scope | Queries | Hit@K | MRR | NDCG@K | Median seconds | Same rankings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| focused | document | 6 | 1.000 | 0.644 | 0.731 | 7.381 | Not tested |
| focused | corpus | 6 | 0.833 | 0.492 | 0.575 | 12.297 | Not tested |

Question SHA-256: `15c2bdb4deabf197e2925283e782ddcfc8e6a759331af76ad23ba92c212f2254`

Passage SHA-256: `7c7d859569de2360ea6e3cba5b228bbb9c76b50d09a86a7c9d13ff110de456df`

- Page retrieval is not answer accuracy.
- Repeatability is measured on this local index and environment only.
- Timing includes first-query model startup; not a production load test.
- Dataset independence and split quality require separate review.
