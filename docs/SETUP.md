# Setup and usage

Run commands from the repository root after the README's installation steps.
The basic app uses BM25 without an API key. Downloaded PDFs and models stay under
`data/`, which Git ignores.

## Prepare semantic search

```sh
bankscope embed
bankscope prepare-reranker
```

These commands download free model weights. Queries thereafter use cached local
models. The API selects the standard reranker when prepared, dense search when
only vectors are ready, and BM25 otherwise. Reingestion invalidates vectors and
structured tables; prepare them again afterward. Unchanged vectors are reused.

## Enable the checked American Express table

```sh
bankscope extract-deposits data/financebench/pdfs/AMERICANEXPRESS_2022_10K.pdf \
  --id AMERICANEXPRESS_2022_10K --page 123
```

Select American Express and report year 2022. Try:

- `Break down customer deposits in 2022`
- `How much did customer deposits increase from 2021 to 2022?`

Supported questions use extracted table rows and local Decimal arithmetic. All
categories must reconcile to the reported total in each column. This does not
validate arbitrary tables or generated prose. See the [table validation report](../reports/validation/DEPOSIT_TABLE.md).

## Add JPMorgan Chase reports

```sh
python scripts/fetch_bank_reports.py
bankscope ingest data/reports/pdfs/JPMORGANCHASE_2023_ANNUAL.pdf \
  --id JPMORGANCHASE_2023_ANNUAL --company 'JPMorgan Chase' --year 2023 \
  --extractor pdfium \
  --url https://www.jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/investor-relations/documents/annualreport-2023.pdf
bankscope ingest data/reports/pdfs/JPMORGANCHASE_2022_ANNUAL.pdf \
  --id JPMORGANCHASE_2022_ANNUAL --company 'JPMorgan Chase' --year 2022 \
  --extractor pdfium \
  --url https://www.jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/investor-relations/documents/annualreport-2022.pdf
bankscope extract-segment-deposits data/reports/pdfs/JPMORGANCHASE_2023_ANNUAL.pdf \
  --id JPMORGANCHASE_2023_ANNUAL
bankscope embed
```

Select JPMorgan Chase and report year 2023. Ask
`Show period-end deposits by business segment in 2023`.
The frozen adapter rejects the 2022 layout; that report remains searchable.
See the [transfer experiment](../reports/validation/JPMORGAN_EXPANSION.md).

## Optional AI generation

Copy `.env.example` to `.env`, then enter the key privately in your editor. Set
`BANKSCOPE_ENABLE_PAID=1` only when you intend to use the provider. Entry points load
`.env`; explicitly exported shell variables take precedence. Restart the server
after editing settings. Never commit or paste the key into chat.

```sh
bankscope ask 'What were total revenues?' \
  --company 'American Express' --year 2022 --strategy rerank --generate
```

Generation uses GPT-4o mini with at most 600 output tokens and no automatic retries.
The API accepts `generate_answer: true`; the UI shows the option when configured.
`BANKSCOPE_MAX_CALLS` defaults to twenty attempts, including failures, tracked in a
local usage ledger. This is a request-count cap, not an account-wide dollar limit.
Citations and monetary magnitudes are checked, but entailment, completeness,
consolidated scope and row/year alignment are not established by those checks.

## Evaluate retrieval

```sh
bankscope evaluate --mode document --strategy rerank
bankscope evaluate --mode corpus --strategy rerank
python -m bankscope.experiments \
  --questions datasets/jpm_retrieval_diagnostics.jsonl \
  --strategies bm25 dense hybrid rerank --repeats 2 \
  --output reports/experiments/my-new-run
```

The experiment runner requires a new output directory, records data/code
fingerprints and query traces, and makes no paid calls. Gold labels never enter
the source index or generation context. Only questions with indexed evidence
are scored; missing-document counts are reported.

`--strategy focused` enables the experimental financial query-expansion method.
The default remains `rerank` because the development improvement has a regression
on an earlier question. See the [retrieval audit](../reports/validation/RETRIEVAL_MISS_AUDIT.md).

For the separate five-report banking pilot, run
`PYTHONPATH=. python scripts/prepare_pilot.py` after downloading the American
Express and JPMorgan FinanceBench sources. The pilot uses a separate local index.
Preparation downloads public sources; it does not generate paid answers.
[Answer-evaluation instructions](ANSWER_EVALUATION.md) describe cost approval,
private audit output and the human-review rubric.

## Tests and packaging

```sh
python -m pytest --cov=bankscope --cov-branch --cov-fail-under=80
```

Provider responses are mocked in tests. Optional source-PDF integration tests skip
in a clean checkout. CI runs the offline suite after dependency installation.
`requirements-lock.txt` is a tested macOS/Python environment snapshot; `pyproject.toml`
is the portable dependency specification. The Dockerfile supplies a base BM25
image; Docker builds and public hosting still need verification.
