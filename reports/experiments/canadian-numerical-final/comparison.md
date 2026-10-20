# Retrieval experiment

Created: 2026-10-20T17:35:58.899482+00:00

| Method | Scope | Queries | Hit@K | MRR | NDCG@K | Median seconds | Same rankings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| financial | document | 6 | 1.000 | 1.000 | 1.000 | 3.347 | True |
| financial | corpus | 6 | 1.000 | 1.000 | 1.000 | 3.169 | True |

Question SHA-256: `ad4891d4a5f88a1966347cdcd353f4ac29689c20a6448289a51c5cabb0d2e384`

Passage SHA-256: `17e01c066c6f1ffba24b74da99fa97eff93c44b61cc81c674f1fe347461240b5`

- Page retrieval is not answer accuracy.
- Repeatability is measured on this local index and environment only.
- Timing includes first-query model startup; not a production load test.
- Dataset independence and split quality require separate review.
