# Retrieval experiment

Created: 2026-10-20T17:32:56.039300+00:00

| Method | Scope | Queries | Hit@K | MRR | NDCG@K | Median seconds | Same rankings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| financial | document | 8 | 1.000 | 0.906 | 0.929 | 3.469 | Not tested |
| financial | corpus | 8 | 1.000 | 0.906 | 0.929 | 3.346 | Not tested |

Question SHA-256: `383b72101d7d58f07d1678fb326f5f43fdb64bd82041c02fc918e8e03ed28427`

Passage SHA-256: `17e01c066c6f1ffba24b74da99fa97eff93c44b61cc81c674f1fe347461240b5`

- Page retrieval is not answer accuracy.
- Repeatability is measured on this local index and environment only.
- Timing includes first-query model startup; not a production load test.
- Dataset independence and split quality require separate review.
