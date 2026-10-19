# Demonstrating and explaining BankScope

## Three-minute demonstration

1. Select JPMorgan Chase, report 2023. Ask `Show period-end deposits by business
   segment in 2023`. Explain the distinction between segment and product categories.
2. Inspect the original source page. Show year/unit headings and the separate
   period-end/average columns. Explain why matching a number alone is insufficient.
3. Select the 2022 report and ask the equivalent question. Show source excerpts
   instead of a structured table. Explain that the frozen extractor rejected this
   layout rather than serving an unchecked calculation.
4. Open `reports/validation/JPMORGAN_EXPANSION.md`. Explain that BM25 found all six diagnostic
   pages while corpus reranking found five. These six questions concentrate on two
   pages; they are not an unbiased general benchmark.
5. Show a reproducible experiment's JSON trace, source/data fingerprints and repeat
   results. Distinguish code coverage, page retrieval and generated-answer quality.

## Questions to be able to answer

- Why can a cross-encoder improve ranking yet lose a relevant page at K=5?
- How do document-scoped and corpus-wide evaluation differ?
- What does a physical page citation prove, and what does it leave unverified?
- Why use Decimal arithmetic for financial tables?
- What causes the 2022 table adapter to reject extraction?
- What changes when the corpus grows beyond in-memory dense scoring?
- Which calls cost money and how is the local attempt cap enforced?

## Defensible resume draft

Built a banking-report research prototype over 952 pages of public annual reports
using FastAPI, SQLite FTS5, local BGE embeddings and MiniLM cross-encoder reranking;
implemented page citations, scoped deposit-table extraction with reconciliation,
and reproducible retrieval experiments with per-query traces and data fingerprints.

Add current test/coverage figures only alongside the committed verification report.
Do not describe it as production-deployed, general financial advice, or validated
LLM answer accuracy. Know how each component works before using this in interviews.
