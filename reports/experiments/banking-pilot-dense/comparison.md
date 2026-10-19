# Retrieval experiment

Created: 2026-10-19T20:49:24.328237+00:00

| Method | Scope | Queries | Hit@K | MRR | NDCG@K | Median seconds | Same rankings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dense | document | 12 | 0.333 | 0.100 | 0.157 | 0.032 | Not tested |
| dense | corpus | 12 | 0.167 | 0.058 | 0.085 | 0.076 | Not tested |

Question SHA-256: `26f3b152b1a27281073e3d2c8b6dcc28d23495d2663ccbc3b6ab2d4c5ba5017b`

Passage SHA-256: `0da1697a92eb36312afef08148b52d9981f23060399fd2c37832e26722d9c01c`

- Page retrieval is not answer accuracy.
- Repeatability is measured on this local index and environment only.
- Timing includes first-query model startup; not a production load test.
- Dataset independence and split quality require separate review.
