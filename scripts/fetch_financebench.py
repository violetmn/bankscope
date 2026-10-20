"""Fetch labels separately from source PDFs. No labels enter retrieval."""
import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = "https://raw.githubusercontent.com/patronus-ai/financebench/"


def download(url, target, pdf=False, user_agent="BankScope-research/0.1"):
    if target.exists():
        return
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=60) as response:
        body = response.read(50_000_001)
    if len(body) > 50_000_000:
        raise ValueError("Download exceeds 50 MB")
    if pdf and not body.startswith(b"%PDF-"):
        raise ValueError("Response is not a PDF")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--revision", default="main")
    p.add_argument("--company", default="American Express")
    p.add_argument("--max-docs", type=int, default=1)
    args = p.parse_args()
    if args.max_docs < 0 or not re.fullmatch(r"[A-Za-z0-9_.-]+", args.revision):
        p.error("Invalid revision or max-docs")
    root = Path("data/financebench")
    root.mkdir(parents=True, exist_ok=True)
    for name in ["financebench_document_information.jsonl", "financebench_open_source.jsonl"]:
        download(f"{ROOT}{args.revision}/data/{name}", root / name)
    metadata = [json.loads(x) for x in (root / "financebench_document_information.jsonl").read_text().splitlines()]
    questions = [json.loads(x) for x in (root / "financebench_open_source.jsonl").read_text().splitlines()]
    tested = {q["doc_name"] for q in questions}
    selected = [d for d in metadata if d["company"].casefold() == args.company.casefold() and d["doc_name"] in tested]
    if not selected and args.max_docs:
        raise SystemExit("No matching company. Available: " + ", ".join(sorted({q['company'] for q in questions})))
    manifest = []
    for d in selected[:args.max_docs]:
        name = d["doc_name"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise ValueError("Unsafe name")
        target = root / "pdfs" / (name + ".pdf")
        url = f"{ROOT}{args.revision}/pdfs/{urllib.parse.quote(name)}.pdf"
        download(url, target, pdf=True)
        manifest.append({**d, "local_path": str(target), "download_url": url,
                         "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        print("Downloaded", name)
    out = root / (re.sub(r"\W+", "_", args.company) + "_manifest.json")
    out.write_text(json.dumps({"repository": ROOT, "revision": args.revision, "documents": manifest}, indent=2))
    print(f"Questions: {len(questions)}. Selected PDFs: {len(manifest)}. Manifest: {out}")


if __name__ == "__main__":
    main()
