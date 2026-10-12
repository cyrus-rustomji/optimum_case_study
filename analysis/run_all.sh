#!/usr/bin/env bash
# Rebuild everything from the raw CSVs: checks -> SQL pipeline -> model -> charts -> deck.
# Usage: ./run_all.sh            (uses cached external L1 cost data in external/raw/)
#        ./run_all.sh --refetch  (re-downloads DefiLlama / growthepie first; on-chain is attempted, may be rate-limited)
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
[ -x "$PY" ] || { python3 -m venv .venv && $PY -m pip install -q -r requirements.txt; }
if [[ "${1:-}" == "--refetch" ]]; then rm -f external/raw/llama_*.json external/raw/gtp_*.json; $PY external/fetch_l1_costs.py; fi
[ -f external/l1_costs_daily.csv ] || $PY external/fetch_l1_costs.py --skip-onchain
cd src
../$PY checks.py
../$PY analysis.py > /dev/null
../$PY growth_model.py > /dev/null
[ -f charts.py ] && ../$PY charts.py
[ -f build_deck.py ] && ../$PY build_deck.py
echo "done: outputs/ and deck/ rebuilt"
