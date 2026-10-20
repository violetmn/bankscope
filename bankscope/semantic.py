"""Local dense retrieval plus reciprocal-rank fusion with the BM25 baseline.

Only the explicit embed command downloads model weights. Queries use cached files.
"""
import hashlib
import re
from itertools import islice
from functools import lru_cache
from pathlib import Path

MODEL = "BAAI/bge-small-en-v1.5"
RERANKER = "Xenova/ms-marco-MiniLM-L-6-v2"
CACHE = "data/models"


@lru_cache(maxsize=1)
def encoder():
    from fastembed import TextEmbedding
    return TextEmbedding(MODEL, cache_dir=CACHE, threads=2, local_files_only=True)


@lru_cache(maxsize=1)
def reranker():
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    return TextCrossEncoder(RERANKER, cache_dir=CACHE, threads=2, local_files_only=True)


def prepare_reranker():
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    model = TextCrossEncoder(RERANKER, cache_dir=CACHE, threads=2)
    list(model.rerank("model readiness check", ["A financial report."]))
    Path(CACHE, "reranker-ready").write_text(RERANKER)
    return {"reranker": RERANKER, "paid_calls": 0}


def reranker_ready():
    return Path(CACHE, "reranker-ready").is_file()


def prepare(store, threads=2):
    from fastembed import TextEmbedding
    import numpy as np
    Path(CACHE).mkdir(parents=True, exist_ok=True)
    model = TextEmbedding(MODEL, cache_dir=CACHE, threads=threads)
    all_rows = store.db.execute("SELECT p.chunk_id, p.text, e.model, e.text_sha256 FROM passages p LEFT JOIN embeddings e ON p.chunk_id=e.chunk_id ORDER BY p.chunk_id").fetchall()
    if not all_rows:
        raise ValueError("Ingest documents before building embeddings")
    rows = [r for r in all_rows if r['model'] != MODEL or r['text_sha256'] != hashlib.sha256(r['text'].encode()).hexdigest()]
    if not rows:
        return {'model':MODEL,'embedded_chunks':0,'reused_chunks':len(all_rows),'paid_calls':0}
    vectors = model.passage_embed([r["text"] for r in rows], batch_size=16)
    pairs = iter(zip(rows, vectors, strict=True))
    while batch := list(islice(pairs, 32)):
        records = []
        for row, vector in batch:
            value = np.asarray(vector, dtype=np.float32)
            value /= max(float(np.linalg.norm(value)), 1e-12)
            records.append((row["chunk_id"], MODEL, hashlib.sha256(row["text"].encode()).hexdigest(), value.tobytes()))
        # Model inference above does not hold a database write transaction.
        with store.db:
            store.db.executemany("INSERT OR REPLACE INTO embeddings VALUES(?,?,?,?)", records)
    encoder.cache_clear()
    return {"model": MODEL, "embedded_chunks": len(rows), 'reused_chunks': len(all_rows)-len(rows), "paid_calls": 0}


def ready(store):
    missing = store.db.execute("""SELECT COUNT(*) FROM passages p LEFT JOIN embeddings e
        ON p.chunk_id=e.chunk_id AND e.model=? WHERE e.chunk_id IS NULL""", (MODEL,)).fetchone()[0]
    count = store.db.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
    return bool(count) and missing == 0


def fuse(dense, lexical, k):
    scores, hits = {}, {}
    for ranking in [dense, lexical]:
        for rank, hit in enumerate(ranking, 1):
            key = hit["chunk_id"]
            scores[key] = scores.get(key, 0) + 1 / (60 + rank)
            hits[key] = hit
    order = sorted(scores, key=lambda key: (-scores[key], key))
    return [{**hits[key], "fusion_score": scores[key]} for key in order[:k]]


def scoped_query(question, company=None, year=None):
    """Avoid redundant entity/period terms dominating an already filtered search."""
    query = question
    if company:
        query = re.sub(re.escape(company) + r"(?:['’]s|['’])?", " ", query, flags=re.I)
    if year is not None:
        query = re.sub(r"\b(?:FY)?" + str(year) + r"\b", " ", query, flags=re.I)
    return " ".join(query.split()).strip(" ?.,") or question


def distinct_pages(hits, k):
    selected, seen = [], set()
    for hit in hits:
        page = (hit["doc_id"], hit["page"])
        if page not in seen:
            selected.append(hit)
            seen.add(page)
        if len(selected) == k:
            break
    return selected


def semantic_search(store, question, k, company, year, doc_id, strategy):
    import numpy as np
    if not ready(store):
        raise ValueError("Semantic index is missing or stale. Run bankscope embed after ingestion.")
    conditions, args = ["e.model=?"], [MODEL]
    for field, value in [("company", company), ("year", year), ("id", doc_id)]:
        if value is not None:
            conditions.append(f"d.{field}=?")
            args.append(value)
    rows = store.db.execute("""SELECT p.text,p.doc_id,p.page,p.chunk_id,d.company,d.year,d.url,
        e.vector FROM passages p JOIN documents d ON p.doc_id=d.id
        JOIN embeddings e ON p.chunk_id=e.chunk_id WHERE """ + " AND ".join(conditions)
        + " ORDER BY p.chunk_id", args).fetchall()
    if not rows or not question.strip():
        return []
    scoped = scoped_query(question, company or (rows[0]["company"] if doc_id else None),
                          year or (rows[0]["year"] if doc_id else None))
    query = np.asarray(next(encoder().query_embed(scoped)), dtype=np.float32)
    query /= max(float(np.linalg.norm(query)), 1e-12)
    matrix = np.stack([np.frombuffer(r["vector"], dtype=np.float32) for r in rows])
    scores = matrix @ query
    order = np.argsort(-scores, kind="stable")[:max(20, k)]
    dense = []
    for index in order:
        h = dict(rows[int(index)])
        del h["vector"]
        h["page"] = int(h["page"])
        h["similarity"] = float(scores[index])
        h["citation"] = f"[{h['doc_id']}, PDF page {h['page']}]"
        h["source_url"] = h["url"].split("#")[0] + f"#page={h['page']}" if h["url"] else ""
        dense.append(h)
    if strategy == "dense":
        return distinct_pages(dense, k)
    lexical = store.search(scoped, 20, company, year, doc_id, strategy="bm25")
    if strategy == "rerank":
        if not reranker_ready():
            raise ValueError("Run bankscope prepare-reranker before using reranking.")
        candidates = list({h["chunk_id"]: h for h in dense + lexical}.values())
        scores = list(reranker().rerank(scoped, [h["text"] for h in candidates], batch_size=8))
        ranked = sorted(({**hit, "rerank_score": float(score)} for hit, score in zip(candidates, scores, strict=True)),
                        key=lambda h: (-h["rerank_score"], h["chunk_id"]))
        return distinct_pages(ranked, k)
    return distinct_pages(fuse(dense, lexical, len(dense) + len(lexical)), k)
