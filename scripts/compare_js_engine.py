#!/usr/bin/env python3
"""Compare the browser engine with the pandas indicators on one fixed cache export."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from elder_indicators.config import load_config
from elder_indicators.indicators import calculate_indicators
from elder_indicators.signals import _screen_one, _screen_two
from market_data.bars import aggregate_weekly_from_daily


DEFAULT_INPUT = ROOT / "presentation/query/validation/600519_SH_daily.json"
TARGET_DATE = "2026-11-16"
METRICS = (
    "ema",
    "macd",
    "signal",
    "histogram",
    "rsi",
    "force_index",
    "bull_power",
    "bear_power",
    "stoch_k",
    "stoch_d",
    "trigger_price",
)

NODE_RUNNER = r"""
const fs = require('fs');
const vm = require('vm');
global.window = global;
vm.runInThisContext(fs.readFileSync(process.argv[1], 'utf8'));
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const {daily, raw, weekly, params, market, target_date} = input;
const values = ElderEngine.calculate(daily, params);
const directions = ElderEngine.screenOne(weekly, params);
const i = daily.findIndex((row) => row.date === target_date);
if (i < 1) throw new Error(`Target date ${target_date} is missing from daily input`);
let wi = -1;
for (let j = 0; j < weekly.length; j += 1) if (weekly[j].date <= target_date) wi = j;
const direction = wi >= 0 ? directions[wi] : 0;
const setup_index = i - 1;
const setup = ElderEngine.screenTwo(daily, values, setup_index, direction, params);
const previous = raw[setup_index];
const trigger_price = direction > 0
  ? previous.high + params.breakout_offset_ticks * market.price_tick
  : direction < 0
    ? previous.low - params.breakout_offset_ticks * market.price_tick
    : null;
const current = raw[i];
const triggered = direction > 0
  ? current.high >= trigger_price
  : direction < 0
    ? current.low <= trigger_price
    : false;
const output = Object.fromEntries([
  ['ema', values.ema[i]], ['macd', values.macd[i]],
  ['signal', values.macdSignal[i]], ['histogram', values.histogram[i]],
  ['rsi', values.rsi[i]], ['force_index', values.force[i]],
  ['bull_power', values.bull[i]], ['bear_power', values.bear[i]],
  ['stoch_k', values.stoch[i]], ['stoch_d', values.stochD[i]],
  ['trigger_price', trigger_price], ['direction', direction],
  ['setup', setup], ['triggered', triggered],
  ['previous_date', previous.date], ['previous_high_raw', previous.high],
  ['previous_low_raw', previous.low], ['bar_high_raw', current.high],
  ['bar_low_raw', current.low], ['weekly_date', weekly[wi]?.date ?? null],
]);
process.stdout.write(JSON.stringify(output));
"""


def _read_cache(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp").sort_index()


def export_fixed_input(path: Path) -> None:
    config = load_config(ROOT / "docs/indicators.yaml")
    code = "600519_SH"
    qfq = _read_cache(ROOT / f"data/cache/{code}_daily_qfq.csv")
    raw = _read_cache(ROOT / f"data/cache/{code}_daily_raw.csv")
    qfq = qfq.loc[qfq["is_closed"].fillna(False)]
    raw = raw.loc[raw["is_closed"].fillna(False)]
    common_dates = sorted(set(qfq.index.date) & set(raw.index.date))
    qfq = qfq.loc[[stamp.date() in common_dates for stamp in qfq.index]]
    raw = raw.loc[[stamp.date() in common_dates for stamp in raw.index]]
    weekly = aggregate_weekly_from_daily(qfq, config["market"])

    def rows(frame: pd.DataFrame, *, weekly_rows: bool = False) -> list[dict[str, Any]]:
        output = []
        for timestamp, row in frame.iterrows():
            output.append({
                "date": timestamp.date().isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            })
        return output

    raw_rows = rows(raw)
    payload = {
        "symbol": "600519.SH",
        "source": "data/cache/600519_SH_daily_qfq.csv and daily_raw.csv",
        "target_date": TARGET_DATE,
        "daily": rows(qfq),
        "raw": raw_rows,
        "weekly": rows(weekly, weekly_rows=True),
        "params": config["params"],
        "market": config["market"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT)} ({len(payload['daily'])} daily, {len(payload['weekly'])} complete weekly bars)")


def _python_values(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    daily = pd.DataFrame(payload["daily"])
    daily.index = pd.to_datetime(daily.pop("date") + " 15:00:00")
    raw = pd.DataFrame(payload["raw"])
    raw.index = pd.to_datetime(raw.pop("date") + " 15:00:00")
    weekly = pd.DataFrame(payload["weekly"])
    weekly.index = pd.to_datetime(weekly.pop("date") + " 15:00:00")
    indicators = calculate_indicators(daily, config["params"])
    directions = _screen_one(weekly, config["params"]).set_index("timestamp")
    setups = _screen_two(daily, config["params"]).set_index("timestamp")
    timestamp = pd.Timestamp(payload["target_date"] + " 15:00:00")
    index = daily.index.get_loc(timestamp)
    previous_timestamp = daily.index[index - 1]
    direction_row = directions.loc[directions.index <= timestamp].iloc[-1]
    direction = int(direction_row["direction"])
    setup_row = setups.loc[previous_timestamp]
    setup = bool(setup_row["long_setup"] if direction == 1 else setup_row["short_setup"] if direction == -1 else False)
    previous_raw = raw.loc[previous_timestamp]
    current_raw = raw.loc[timestamp]
    params = config["params"]
    market = config["market"]
    trigger_price = None
    if direction == 1:
        trigger_price = float(previous_raw["high"]) + float(params["breakout_offset_ticks"]) * float(market["price_tick"])
        triggered = bool(float(current_raw["high"]) >= trigger_price)
    elif direction == -1:
        trigger_price = float(previous_raw["low"]) - float(params["breakout_offset_ticks"]) * float(market["price_tick"])
        triggered = bool(float(current_raw["low"]) <= trigger_price)
    else:
        triggered = False
    row = indicators.loc[timestamp]
    return {
        "ema": float(row["ema"]),
        "macd": float(row["macd"]),
        "signal": float(row["signal"]),
        "histogram": float(row["histogram"]),
        "rsi": float(row["rsi"]),
        "force_index": float(row["force_index"]),
        "bull_power": float(row["bull_power"]),
        "bear_power": float(row["bear_power"]),
        "stoch_k": float(row["stoch_k"]),
        "stoch_d": float(row["stoch_d"]),
        "trigger_price": trigger_price,
        "direction": direction,
        "setup": setup,
        "triggered": triggered,
        "previous_date": previous_timestamp.date().isoformat(),
        "previous_high_raw": float(previous_raw["high"]),
        "previous_low_raw": float(previous_raw["low"]),
        "bar_high_raw": float(current_raw["high"]),
        "bar_low_raw": float(current_raw["low"]),
        "weekly_date": directions.index[directions.index <= timestamp][-1].date().isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--export-input", action="store_true", help="rebuild the committed input JSON from the local AkShare cache")
    args = parser.parse_args()
    if args.export_input:
        export_fixed_input(args.input)
        return
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    config = load_config(ROOT / "docs/indicators.yaml")
    payload["params"] = config["params"]
    payload["market"] = config["market"]
    js = subprocess.run(
        ["node", "-e", NODE_RUNNER, str(ROOT / "presentation/query/engine.js")],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=True,
        cwd=ROOT,
    )
    js_values = json.loads(js.stdout)
    python_values = _python_values(payload, config)
    input_hash = hashlib.sha256(args.input.read_bytes()).hexdigest()
    print(f"Fixed input: {args.input.relative_to(ROOT)}; symbol={payload['symbol']}; date={payload['target_date']}")
    print(f"Input SHA-256: {input_hash}")
    print(f"Daily bars={len(payload['daily'])}; complete weekly bars={len(payload['weekly'])}; raw reference date={python_values['previous_date']}")
    print("metric                 Python                 JavaScript             relative error")
    maximum_error = 0.0
    for key in METRICS:
        python_value = python_values[key]
        js_value = js_values[key]
        if python_value is None or js_value is None:
            error = 0.0 if python_value is js_value else float("inf")
        else:
            error = abs(python_value - js_value) / max(abs(python_value), abs(js_value), 1e-12)
        maximum_error = max(maximum_error, error)
        print(f"{key:22} {str(python_value):22} {str(js_value):22} {error:.8%}")
    boolean_keys = ("direction", "setup", "triggered")
    matches = all(python_values[key] == js_values[key] for key in boolean_keys)
    for key in boolean_keys:
        print(f"{key:22} {python_values[key]!s:22} {js_values[key]!s:22} {'MATCH' if python_values[key] == js_values[key] else 'MISMATCH'}")
    print(f"T-1 raw high={python_values['previous_high_raw']:.2f}; T-1 raw low={python_values['previous_low_raw']:.2f}; signal-day raw high={python_values['bar_high_raw']:.2f}; raw low={python_values['bar_low_raw']:.2f}")
    print(f"Maximum numeric relative error={maximum_error:.8%}; boolean checks={'PASS' if matches else 'FAIL'}")
    if maximum_error >= 0.005 or not matches:
        raise SystemExit("JS/Python parity check failed")


if __name__ == "__main__":
    main()
