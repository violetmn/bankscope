#!/bin/bash
# User-approved one-off pilot: at most 20 calls, estimated below US$0.10.
set -euo pipefail
cd "$(dirname "$0")/.."
# The Python entry point reads .env privately; no key is echoed.
export BANKSCOPE_ENABLE_PAID=1
export BANKSCOPE_MAX_CALLS=20
.venv/bin/python -m bankscope.answer_evaluation execute \
  --plan data/benchmarks/pilot-v1/answer-plan.json \
  --output data/benchmarks/pilot-v1/real-answer-run \
  --approved-cap-usd 0.10
echo 'Run saved to data/benchmarks/pilot-v1/real-answer-run. Answers await review.'
