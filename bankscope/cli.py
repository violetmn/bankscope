import argparse
import json
from bankscope.store import Store
from bankscope.evaluation import evaluate
from bankscope.generation import generate


def main():
    from bankscope.config import load_private_env
    load_private_env()
    parser = argparse.ArgumentParser(prog="bankscope")
    parser.add_argument("--db", default="data/index.sqlite3")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("documents")
    sub.add_parser("embed")
    sub.add_parser("prepare-page-contexts")
    sub.add_parser("prepare-reranker")
    tables = sub.add_parser("extract-deposits")
    tables.add_argument("path")
    tables.add_argument("--id", required=True)
    tables.add_argument("--page", required=True, type=int)
    segment = sub.add_parser('extract-segment-deposits')
    segment.add_argument('path')
    segment.add_argument('--id', required=True)
    segment.add_argument('--page', type=int)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("path")
    ingest.add_argument('--extractor', choices=['pdfplumber','pdfium'], default='pdfplumber')
    for key in ["id", "company", "year", "url"]:
        ingest.add_argument("--" + key, required=True, type=int if key == "year" else str)
    ask = sub.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--company")
    ask.add_argument("--year", type=int)
    ask.add_argument("--generate", action="store_true")
    ask.add_argument("--strategy", choices=["bm25", "dense", "hybrid", "rerank", "focused", "financial"], default="bm25")
    ev = sub.add_parser("evaluate")
    ev.add_argument("--questions", default="data/financebench/financebench_open_source.jsonl")
    ev.add_argument("--mode", choices=["document", "corpus"], default="document")
    ev.add_argument("--k", type=int, default=5)
    ev.add_argument("--strategy", choices=["bm25", "dense", "hybrid", "rerank", "focused", "financial"], default="bm25")
    args = parser.parse_args()
    store = Store(args.db)
    try:
        if args.command == "prepare-page-contexts":
            from bankscope.page_contexts import prepare
            result = prepare(store)
        elif args.command == "ingest":
            result = store.ingest_pdf(args.path, args.id, args.company, args.year, args.url, args.extractor)
        elif args.command == "documents":
            result = store.documents()
        elif args.command == "evaluate":
            result = evaluate(store, args.questions, args.k, args.mode, args.strategy)
        elif args.command == "embed":
            from bankscope.semantic import prepare
            result = prepare(store)
        elif args.command == "prepare-reranker":
            from bankscope.semantic import prepare_reranker
            result = prepare_reranker()
        elif args.command == "extract-deposits":
            from bankscope.tables import extract_deposits
            result = extract_deposits(store, args.path, args.id, args.page)
        elif args.command == 'extract-segment-deposits':
            from bankscope.segment_tables import extract_segment_deposits
            result = extract_segment_deposits(store, args.path, args.id, args.page)
        else:
            hits = store.search(args.question, company=args.company, year=args.year, strategy=args.strategy)
            result = generate(args.question, hits) if args.generate else {"mode": "evidence_search", "sources": hits}
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        store.close()


if __name__ == "__main__":
    main()
