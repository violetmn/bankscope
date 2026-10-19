"""Page-level retrieval evaluation; gold labels are never indexed."""
import json
import math


def evaluate(store, question_file, k=5, mode="document", strategy="bm25"):
    if mode not in {"document", "corpus"}:
        raise ValueError("mode must be document or corpus")
    if not 1 <= k <= 20:
        raise ValueError("k must be between 1 and 20")
    rows, skipped = [], 0
    indexed = {d["id"] for d in store.documents()}
    with open(question_file, encoding="utf-8") as source:
        questions = [json.loads(line) for line in source if line.strip()]
    for q in questions:
        evidence = q.get("evidence", [])
        # The release uses doc_name; older documentation calls it evidence_doc_name.
        gold = {(e.get("doc_name") or e.get("evidence_doc_name") or q["doc_name"],
                 int(e["evidence_page_num"]) + 1) for e in evidence}
        if not gold or any(d not in indexed for d, _ in gold):
            skipped += 1
            continue
        hits = store.search(q["question"], k=k, doc_id=q["doc_name"] if mode == "document" else None, strategy=strategy)
        # Multiple chunks on the same page count once for gain/recall.
        seen, gains = set(), []
        for h in hits:
            page = (h["doc_id"], h["page"])
            gains.append(int(page in gold and page not in seen))
            seen.add(page)
        rank = next((i for i, g in enumerate(gains, 1) if g), None)
        dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
        ideal = sum(1 / math.log2(i + 2) for i in range(min(k, len(gold))))
        rows.append({"id": q.get('id',q.get('financebench_id')), "hit": int(rank is not None),
                     "rr": 1 / rank if rank else 0, "recall": sum(gains) / len(gold),
                     "ndcg": dcg / ideal if ideal else 0})
    n = len(rows)
    return {"retriever": strategy, "mode": mode, "k": k,
            "evaluated": n, "skipped_missing_documents": skipped,
            "hit_rate": sum(r["hit"] for r in rows) / n if n else None,
            "mrr": sum(r["rr"] for r in rows) / n if n else None,
            "page_recall": sum(r["recall"] for r in rows) / n if n else None,
            "ndcg": sum(r["ndcg"] for r in rows) / n if n else None,
            "limitation": "Page-level retrieval only; not answer accuracy or evidence-span support.",
            "results": rows}
