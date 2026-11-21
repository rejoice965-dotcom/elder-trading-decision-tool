from pathlib import Path

import pandas as pd
import pytest

from elder_indicators.config import load_config
from elder_indicators.signals import build_triple_screen_signals
from market_data.provider import load_cached


def test_cached_signals_use_previous_raw_session() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_config()
    market = config["market"]
    symbol = "600519.SH"
    try:
        bundle = load_cached(symbol, root / market["cache"]["directory"])
    except FileNotFoundError as error:
        pytest.skip(f"Local 600519.SH replay cache is required: {error.filename}")

    weekly, daily, intraday = bundle.signal_frames(market)
    signals = build_triple_screen_signals(
        weekly, daily, intraday, symbol=symbol, params=config["params"], market=market
    )
    signal_days = signals["timestamp"].dt.normalize()
    audited_days = pd.to_datetime(["2024-12-12", "2025-11-28", "2026-11-16"])
    assert audited_days.isin(signal_days).all()

    # Align against the independent raw daily cache by exact session date.
    previous_raw = bundle.daily_raw.set_axis(bundle.daily_raw.index.normalize()).shift(1)
    expected = previous_raw.loc[signal_days, ["high", "low", "close"]].reset_index(drop=True)
    values = pd.DataFrame(signals["indicator_values"].tolist())
    references = values[["previous_day_high_raw", "previous_day_low_raw", "previous_close_raw"]]
    pd.testing.assert_frame_equal(references.set_axis(expected.columns, axis=1), expected, check_exact=True)
    offset = config["params"]["breakout_offset_ticks"] * market["price_tick"]
    assert values["buy_stop_price_raw"].tolist() == pytest.approx(expected["high"] + offset)
    assert values["sell_stop_price_raw"].tolist() == pytest.approx(expected["low"] - offset)
