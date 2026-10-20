# Retrieval experiment

Created: 2026-10-20T16:58:42.371187+00:00

| Method | Scope | Queries | Hit@K | MRR | NDCG@K | Median seconds | Same rankings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bm25 | document | 6 | 0.000 | 0.000 | 0.000 | 0.010 | Not tested |
| bm25 | corpus | 6 | 0.000 | 0.000 | 0.000 | 0.012 | Not tested |
| rerank | document | 6 | 0.000 | 0.000 | 0.000 | 3.403 | Not tested |
| rerank | corpus | 6 | 0.000 | 0.000 | 0.000 | 3.300 | Not tested |

Question SHA-256: `ad4891d4a5f88a1966347cdcd353f4ac29689c20a6448289a51c5cabb0d2e384`

Passage SHA-256: `17e01c066c6f1ffba24b74da99fa97eff93c44b61cc81c674f1fe347461240b5`

- Page retrieval is not answer accuracy.
- Repeatability is measured on this local index and environment only.
- Timing includes first-query model startup; not a production load test.
- Dataset independence and split quality require separate review.
