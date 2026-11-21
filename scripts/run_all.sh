#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${WB_PYTHON:-$PROJECT_ROOT/../.venv-vnpy/bin/python}"
SYMBOL="${1:?usage: scripts/run_all.sh SYMBOL NAME}"
NAME="${2:?usage: scripts/run_all.sh SYMBOL NAME}"

cd "$PROJECT_ROOT"
RUN_DIR="$(mktemp -d)"
trap 'rm -rf "$RUN_DIR"' EXIT
SIGNALS_PATH="$RUN_DIR/signals.csv"

printf '[1/4] Loading local qfq/raw caches for %s\n' "$SYMBOL"
"$PYTHON_BIN" - "$SYMBOL" <<'PY'
import sys
from pathlib import Path

from elder_indicators.config import load_config
from market_data.provider import load_cached

symbol = sys.argv[1]
config = load_config()
bundle = load_cached(symbol, Path(config["market"]["cache"]["directory"]))
print(
    f"qfq_daily={len(bundle.daily_qfq)} raw_daily={len(bundle.daily_raw)} "
    f"qfq_60m={len(bundle.intraday_qfq)} raw_60m={len(bundle.intraday_raw)} "
    f"daily_range={bundle.metadata['actual_daily_start']}..{bundle.metadata['actual_daily_end']}"
)
PY

printf '[2/4] Calculating chart indicator series from cached qfq bars\n'
"$PYTHON_BIN" - "$SYMBOL" <<'PY'
import sys
from pathlib import Path

from elder_indicators.config import load_config
from market_data.provider import load_cached
from presentation.dashboard import calculate_display_indicators

config = load_config()
bundle = load_cached(sys.argv[1], Path(config["market"]["cache"]["directory"]))
values = calculate_display_indicators(bundle.daily_qfq, config["params"])
print(f"indicator_rows={len(values)} non_null={values.notna().sum().to_dict()}")
PY

printf '[3/4] Replaying cached bars into signals.csv\n'
"$PYTHON_BIN" -m market_data.replay --symbol "$SYMBOL" --signals-output "$SIGNALS_PATH"

printf '[4/4] Rendering dashboard from cached bars and signals.csv\n'
"$PYTHON_BIN" -m presentation.build_dashboard \
  --symbol "$SYMBOL" --name "$NAME" --signals "$SIGNALS_PATH" \
  --output examples/triple-screen.html
