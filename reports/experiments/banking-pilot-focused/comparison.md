# Retrieval experiment

Created: 2026-10-19T21:18:06.755358+00:00

| Method | Scope | Queries | Hit@K | MRR | NDCG@K | Median seconds | Same rankings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| focused | document | 12 | 0.667 | 0.431 | 0.491 | 7.727 | Not tested |
| focused | corpus | 12 | 0.667 | 0.431 | 0.491 | 10.485 | Not tested |

Question SHA-256: `26f3b152b1a27281073e3d2c8b6dcc28d23495d2663ccbc3b6ab2d4c5ba5017b`

Passage SHA-256: `0da1697a92eb36312afef08148b52d9981f23060399fd2c37832e26722d9c01c`

- Page retrieval is not answer accuracy.
- Repeatability is measured on this local index and environment only.
- Timing includes first-query model startup; not a production load test.
- Dataset independence and split quality require separate review.
