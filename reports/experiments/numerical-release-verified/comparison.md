# Retrieval experiment

Created: 2026-10-20T17:42:02.838766+00:00

| Method | Scope | Queries | Hit@K | MRR | NDCG@K | Median seconds | Same rankings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| financial | document | 14 | 1.000 | 0.946 | 0.959 | 4.383 | Not tested |
| financial | corpus | 14 | 1.000 | 0.946 | 0.959 | 4.213 | Not tested |

Question SHA-256: `9f194b118b5548d4168211a830e29f4f3d22d75118c491f8af572a59d40d5666`

Passage SHA-256: `17e01c066c6f1ffba24b74da99fa97eff93c44b61cc81c674f1fe347461240b5`

- Page retrieval is not answer accuracy.
- Repeatability is measured on this local index and environment only.
- Timing includes first-query model startup; not a production load test.
- Dataset independence and split quality require separate review.
