# Deposit table workflow: 2026-10-19

## Source and extraction

Source: FinanceBench's `AMERICANEXPRESS_2022_10K.pdf`, physical PDF page 123 / printed
page 120, Note 7, Customer Deposits. PDF SHA-256:
`d3bbc7ab23d6160e07eab50a359e4d68c40efff9fde3baa168e7c40e06f568e6`.
The complete page was rendered and visually reviewed before implementing extraction.

The earlier prose breakdown omitted the sweep-accounts category. The new workflow
reads the deposit-type table directly using pdfplumber cells, preserves all six leaf
categories (without double-counting the certificate heading), maps the adjacent 2022
and 2021 headers, and keeps the source's millions unit and dollar symbol.

Both years' extracted category sums equal their printed totals exactly. Mismatched
totals, missing columns, ambiguous headers, duplicate totals/labels, changed PDFs and
unsupported table shapes are rejected. This is a narrowly supported format, not a
claim that arbitrary financial tables can be parsed reliably.

## App behavior

The local workspace renders both columns and every category, with a link to the
original PDF page. Recognized lookup/breakdown questions use this source table.
Two-year comparisons use Decimal arithmetic and display the inputs/formula, rounding
only the final percentage to two decimal places. Explicit reverse comparisons retain
their direction. An unsupported requested year produces an explicit decline.

This path does not call the LLM. Requests outside the supported vocabulary/intent or
with ambiguous company/report scope fall back to normal RAG. It is not an answer to
causal, regional, product-interest or forecast questions. Annual-report filtering is
separate from the year columns within a report.

## Verification

141 local tests pass, including actual-PDF extraction against visually reviewed
values. The actual-PDF test skips without the downloaded PDF; mocked cell extraction
tests still validate the extraction contract in clean checkouts. Combined line/branch
coverage is approximately 83%. No paid API calls made for this milestone.

Browser checks confirmed readable table rows and columns, reconciliation status and
year-to-year calculation. JavaScript syntax was checked with Node. Source files and
tests are independent of a private API key; extracted runtime tables remain gitignored
inside the local SQLite database.

## Reproduce

```sh
bankscope extract-deposits data/financebench/pdfs/AMERICANEXPRESS_2022_10K.pdf \
  --id AMERICANEXPRESS_2022_10K --page 123
python -m pytest --cov=bankscope --cov-branch
```

Restart any server launched without reload to load the new Python code. The current
dedicated preview is on port 8002; the user's existing key-enabled server on 8001
was left untouched.
