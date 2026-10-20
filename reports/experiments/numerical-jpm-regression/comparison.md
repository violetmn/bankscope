# Retrieval experiment

Created: 2026-10-20T17:34:40.293331+00:00

| Method | Scope | Queries | Hit@K | MRR | NDCG@K | Median seconds | Same rankings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rerank | document | 6 | 1.000 | 0.667 | 0.749 | 3.382 | Not tested |
| rerank | corpus | 6 | 0.833 | 0.617 | 0.670 | 3.578 | Not tested |
| financial | document | 6 | 1.000 | 0.667 | 0.749 | 3.417 | Not tested |
| financial | corpus | 6 | 0.833 | 0.617 | 0.670 | 3.427 | Not tested |

Question SHA-256: `15c2bdb4deabf197e2925283e782ddcfc8e6a759331af76ad23ba92c212f2254`

Passage SHA-256: `17e01c066c6f1ffba24b74da99fa97eff93c44b61cc81c674f1fe347461240b5`

- Page retrieval is not answer accuracy.
- Repeatability is measured on this local index and environment only.
- Timing includes first-query model startup; not a production load test.
- Dataset independence and split quality require separate review.
