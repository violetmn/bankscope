# Retrieval experiment

Created: 2026-10-20T17:31:37.985947+00:00

| Method | Scope | Queries | Hit@K | MRR | NDCG@K | Median seconds | Same rankings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rerank | document | 8 | 0.250 | 0.125 | 0.158 | 3.202 | Not tested |
| rerank | corpus | 8 | 0.000 | 0.000 | 0.000 | 3.464 | Not tested |
| financial | document | 8 | 0.875 | 0.781 | 0.804 | 3.168 | Not tested |
| financial | corpus | 8 | 0.875 | 0.781 | 0.804 | 3.071 | Not tested |

Question SHA-256: `383b72101d7d58f07d1678fb326f5f43fdb64bd82041c02fc918e8e03ed28427`

Passage SHA-256: `17e01c066c6f1ffba24b74da99fa97eff93c44b61cc81c674f1fe347461240b5`

- Page retrieval is not answer accuracy.
- Repeatability is measured on this local index and environment only.
- Timing includes first-query model startup; not a production load test.
- Dataset independence and split quality require separate review.
