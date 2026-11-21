from ast import literal_eval
from pathlib import Path

import pandas as pd

from elder_indicators.config import load_config
from presentation.build_dashboard import render_html
from presentation.dashboard import (
    PROVENANCE,
    build_daily_view,
    build_markers,
    calculate_display_indicators,
    estimate_position,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config()


def test_display_indicators_read_periods_from_params() -> None:
    index = pd.date_range("2026-01-01", periods=40, freq="D")
    close = pd.Series(range(100, 140), index=index, dtype=float)
    frame = pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1000},
        index=index,
    )
    values = calculate_display_indicators(frame, CONFIG["params"])
    assert values["ema"].first_valid_index() == index[CONFIG["params"]["ema_period"] - 1]
    assert values["macd_histogram"].notna().any()
    assert values["force_index"].notna().any()
    assert values["rsi"].notna().any()


def test_markers_match_all_example_signals_and_keep_rule_ids() -> None:
    signals = pd.read_csv(ROOT / "examples" / "signals.csv")
    factors = {pd.Timestamp(value).date().isoformat(): 0.9 for value in signals["timestamp"]}
    markers = build_markers(signals, factors, {}, market=CONFIG["market"])

    assert len(signals) == 120
    assert signals["side"].value_counts().to_dict() == {"SELL": 64, "BUY": 56}
    assert len(markers) == len(signals)
    assert [marker["rule_id"] for marker in markers] == signals["rule_id"].tolist()
    assert [marker["side"] for marker in markers] == signals["side"].tolist()
    assert all(marker["price_qfq"] == marker["price_raw"] * 0.9 for marker in markers)
    assert all(marker["source_quote"] and marker["source_url"] for marker in markers)
    assert all(marker["confidence"] == "A" for marker in markers)
    assert all("source_page" not in marker for marker in markers)

    html = render_html({"markers": markers, "provenance": PROVENANCE, "disclaimer": "仅供研究与回测，不构成投资建议"})
    embedded = html.split("const DATA = ", 1)[1].split(";\nconst {createChart", 1)[0]
    html_markers = __import__("json").loads(embedded)["markers"]
    assert len(html_markers) == 120
    assert [marker["rule_id"] for marker in html_markers] == signals["rule_id"].tolist()
    assert "source_page" not in html
    assert "书中原文" not in html
    assert "仅供研究与回测，不构成投资建议" in html
    assert "依据：公开资料交叉核对，非原书直引" in html
    assert 'value="100000"' in html
    assert "Math.floor(account*DATA.config.risk_pct/distance)" in html
    assert "Math.floor(shares/DATA.config.minimum_lot)*DATA.config.minimum_lot" in html


def test_signal_detail_fields_and_provenance_are_present() -> None:
    signals = pd.read_csv(ROOT / "examples" / "signals.csv")
    row = signals.iloc[0]
    values = literal_eval(row["indicator_values"])
    required = {"direction", "ema_slope", "histogram_slope", "force_index", "bull_power", "bear_power", "stoch_k", "rsi"}
    assert row["rule_id"] == "SYS-05"
    assert required.issubset(values)
    assert row["source_quote"]
    assert row["source_url"].startswith("https://")
    assert row["confidence"] == "A"
    assert pd.isna(row["source_page"])
    assert PROVENANCE == "依据：公开资料交叉核对，非原书直引"


def test_position_estimate_requires_equity_and_rounds_to_board_lot() -> None:
    config = CONFIG["market"]
    missing = estimate_position(
        None, 100.0, 95.0, risk_pct=CONFIG["params"]["risk_per_trade"],
        minimum_lot=config["min_lot"],
        allow_short=config["allow_short"], side="BUY",
    )
    assert missing["shares"] is None
    assert "请填写" in missing["message"]

    estimate = estimate_position(
        100000.0, 100.0, 95.0, risk_pct=CONFIG["params"]["risk_per_trade"],
        minimum_lot=config["min_lot"],
        allow_short=config["allow_short"], side="BUY",
    )
    assert estimate["risk_budget"] == 2000
    assert estimate["shares"] == 400


def test_limit_touch_warning_and_daily_suspension_whitespace() -> None:
    market = CONFIG["market"]
    dates = pd.to_datetime(["2026-01-05 15:00", "2026-01-06 15:00", "2026-01-08 15:00", "2026-01-09 15:00"])
    qfq = pd.DataFrame(
        {"open": [10, 10, 10, 10], "high": [11, 11, 11, 11], "low": [9, 9, 9, 9], "close": [10, 10, 10, 10], "volume": [1, 1, 1, 1]},
        index=dates,
    )
    raw = qfq.copy()
    raw.loc[dates[1], "high"] = 11.0
    rows, factors, limits, summary = build_daily_view(qfq, raw, market, "600519.SH")
    assert any(item["time"] == "2026-01-07" and "open" not in item for item in rows)

    signals = pd.DataFrame(
        [{
            "timestamp": "2026-01-06 10:30:00", "side": "BUY", "price": 10.5,
            "rule_id": "SYS-05", "source_quote": "breakout", "source_url": "https://example.com",
            "confidence": "A", "indicator_values": str({
                "previous_day_low_raw": 9.0, "entry_allowed": True, "at_price_limit": False,
            }),
        }]
    )
    markers = build_markers(signals, factors, limits, market=market)
    assert markers[0]["possible_execution_warning"] is True
