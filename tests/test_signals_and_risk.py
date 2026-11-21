import pandas as pd
import pytest

from elder_indicators.config import load_config
from elder_indicators.risk import monthly_halt, position_size, protected_stop
from elder_indicators.signals import build_triple_screen_signals


CONFIG = load_config()


def sample_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    weekly_index = pd.date_range("2025-10-03", periods=52, freq="W-FRI") + pd.Timedelta("15h")
    weekly_close = pd.Series(
        [float(value**2) for value in range(2, 54)], index=weekly_index, dtype=float
    )
    weekly = pd.DataFrame(
        {
            "open": weekly_close - 1,
            "high": weekly_close + 1,
            "low": weekly_close - 2,
            "close": weekly_close,
            "volume": 10000.0,
            "is_closed": True,
        }
    )
    daily_index = pd.bdate_range("2026-10-01", periods=40) + pd.Timedelta("15h")
    daily_close = pd.Series(range(100, 60, -1), index=daily_index, dtype=float)
    daily = pd.DataFrame(
        {
            "open": daily_close + 0.5,
            "high": daily_close + 1,
            "low": daily_close - 1,
            "close": daily_close,
            "volume": 1000.0,
            "is_closed": True,
        }
    )
    intraday_index = pd.to_datetime([daily_index[-1].date() + pd.Timedelta("1D")]) + pd.Timedelta("10h30m")
    intraday = pd.DataFrame(
        {"open": [64.0], "high": [65.0], "low": [63.0], "close": [64.0], "volume": [100.0], "is_closed": [True]},
        index=intraday_index,
    )
    return weekly, daily, intraday


def test_signals_include_traceability_and_follow_closed_bar_contract() -> None:
    weekly, daily, intraday = sample_frames()
    signals = build_triple_screen_signals(
        weekly,
        daily,
        intraday,
        symbol="600519.SH",
        params=CONFIG["params"],
        market=CONFIG["market"],
    )
    assert not signals.empty
    assert set(signals["side"]) == {"BUY"}
    assert set(signals["rule_id"]) == {"SYS-05"}
    assert signals["source_url"].notna().all()
    assert signals["source_quote"].str.len().le(50).all()
    assert signals["confidence"].eq("A").all()
    assert signals["source_page"].isna().all()
    assert signals["indicator_values"].map(dict).map(lambda values: values["direction"] == 1).all()

    intraday["is_closed"] = False
    intraday["is_resume_first_bar"] = True
    no_signal_before_close = build_triple_screen_signals(
        weekly,
        daily,
        intraday,
        symbol="600519.SH",
        params=CONFIG["params"],
        market=CONFIG["market"],
    )
    assert no_signal_before_close.empty
    intraday["is_closed"] = True
    resumed_bar_signal = build_triple_screen_signals(
        weekly,
        daily,
        intraday,
        symbol="600519.SH",
        params=CONFIG["params"],
        market=CONFIG["market"],
    )
    assert not resumed_bar_signal.empty


def test_future_data_perturbation_does_not_change_past_signals() -> None:
    weekly, daily, intraday = sample_frames()
    baseline = build_triple_screen_signals(
        weekly,
        daily,
        intraday,
        symbol="600519.SH",
        params=CONFIG["params"],
        market=CONFIG["market"],
    )
    cutoff = intraday.index.max()
    weekly_future = pd.DataFrame(
        {"open": [1e6], "high": [1e6], "low": [1e6], "close": [1e6], "volume": [1e9], "is_closed": [True]},
        index=[cutoff + pd.Timedelta("30D")],
    )
    daily_future = pd.DataFrame(
        {"open": [1e6], "high": [1e6], "low": [1e6], "close": [1e6], "volume": [1e9], "is_closed": [True]},
        index=[cutoff + pd.Timedelta("1D")],
    )
    intraday_future = pd.DataFrame(
        {"open": [1e6], "high": [1e6], "low": [1e6], "close": [1e6], "volume": [1e9], "is_closed": [True]},
        index=[cutoff + pd.Timedelta("1D")],
    )
    perturbed = build_triple_screen_signals(
        pd.concat([weekly, weekly_future]),
        pd.concat([daily, daily_future]),
        pd.concat([intraday, intraday_future]),
        symbol="600519.SH",
        params=CONFIG["params"],
        market=CONFIG["market"],
    )
    past = perturbed.loc[pd.to_datetime(perturbed["timestamp"]).le(cutoff)]
    pd.testing.assert_frame_equal(baseline.reset_index(drop=True), past.reset_index(drop=True))


def test_incomplete_same_day_daily_bar_cannot_leak_into_intraday_signal() -> None:
    weekly, daily, intraday = sample_frames()
    baseline = build_triple_screen_signals(
        weekly,
        daily,
        intraday,
        symbol="600519.SH",
        params=CONFIG["params"],
        market=CONFIG["market"],
    )
    same_day_close = intraday.index[0].normalize() + pd.Timedelta("15h")
    same_day = pd.DataFrame(
        {
            "open": [1e6],
            "high": [1e6],
            "low": [1e6],
            "close": [1e6],
            "volume": [1e9],
            "is_closed": [True],
        },
        index=[same_day_close],
    )
    with_future_close = build_triple_screen_signals(
        weekly,
        pd.concat([daily, same_day]),
        intraday,
        symbol="600519.SH",
        params=CONFIG["params"],
        market=CONFIG["market"],
    )
    pd.testing.assert_frame_equal(baseline.reset_index(drop=True), with_future_close.reset_index(drop=True))


@pytest.mark.parametrize("daily_close_hour", [0, 15], ids=["date-labeled", "close-labeled"])
def test_stop_references_use_raw_previous_session_at_the_daily_close(daily_close_hour: int) -> None:
    weekly, daily, intraday = sample_frames()
    intraday.index = intraday.index.normalize() + pd.Timedelta("15h")
    signal_day = daily.iloc[[-1]].set_axis(intraday.index).assign(
        high_raw=90.0, low_raw=40.0, close_raw=80.0,
    )
    signal_day.index = signal_day.index.normalize() + pd.Timedelta(hours=daily_close_hour)
    daily = daily.assign(
        high_raw=daily["high"] + 1, low_raw=daily["low"] - 1, close_raw=daily["close"] + 1,
    )
    previous = daily.iloc[-1]
    earlier = daily.iloc[-2]
    assert previous["high_raw"] != earlier["high_raw"]
    assert previous["low_raw"] != earlier["low_raw"]

    signals = build_triple_screen_signals(
        weekly,
        pd.concat([daily, signal_day]),
        intraday,
        symbol="600519.SH",
        params=CONFIG["params"],
        market=CONFIG["market"],
    )

    assert signals["side"].tolist() == ["BUY"]
    values = signals.iloc[0]["indicator_values"]
    assert values["previous_day_high_raw"] == previous["high_raw"]
    assert values["previous_day_low_raw"] == previous["low_raw"]
    assert values["previous_close_raw"] == previous["close_raw"]
    tick_offset = CONFIG["params"]["breakout_offset_ticks"] * CONFIG["market"]["price_tick"]
    assert values["buy_stop_price_raw"] == pytest.approx(previous["high_raw"] + tick_offset)
    assert values["sell_stop_price_raw"] == pytest.approx(previous["low_raw"] - tick_offset)


def test_suspended_intraday_bar_cannot_emit_signal() -> None:
    weekly, daily, intraday = sample_frames()
    intraday["is_suspended"] = True
    signals = build_triple_screen_signals(
        weekly,
        daily,
        intraday,
        symbol="600519.SH",
        params=CONFIG["params"],
        market=CONFIG["market"],
    )
    assert signals.empty


def test_risk_rules_and_lot_rounding() -> None:
    assert position_size(100000, 10, 9, CONFIG["params"], CONFIG["market"]) == 2000
    assert position_size(10000, 100, 99.99, CONFIG["params"], CONFIG["market"]) == 100
    assert monthly_halt(100000, 93000, CONFIG["params"])
    assert not monthly_halt(100000, 95000, CONFIG["params"])
    assert protected_stop(10, 14, CONFIG["params"]) == 12
