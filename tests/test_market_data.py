import numpy as np
import pandas as pd

from elder_indicators.config import load_config
from elder_indicators.market_rules import can_sell, price_limits, round_to_lot
from market_data.bars import (
    annotate_intraday_status,
    aggregate_daily_from_60m,
    aggregate_weekly_from_daily,
    apply_adjustment_factor,
    normalize_bars,
)
from market_data.provider import _at_daily_close


MARKET = load_config()["market"]


def test_daily_aggregation_requires_all_configured_bars() -> None:
    index = pd.to_datetime(
        ["2026-01-05 10:30", "2026-01-05 11:30", "2026-01-05 14:00", "2026-01-05 15:00"]
    )
    bars = pd.DataFrame(
        {
            "open_qfq": [10, 11, 12, 11],
            "high_qfq": [11, 12, 13, 12],
            "low_qfq": [9, 10, 11, 10],
            "close_qfq": [11, 12, 11, 12],
            "volume": [100, 200, 300, 400],
            "close": [11, 12, 11, 12],
        },
        index=index,
    )
    result = aggregate_daily_from_60m(bars, MARKET)
    assert len(result) == 1
    assert result.iloc[0]["open"] == 10
    assert result.iloc[0]["high"] == 13
    assert result.iloc[0]["low"] == 9
    assert result.iloc[0]["close"] == 12
    assert result.iloc[0]["volume"] == 1000
    assert aggregate_daily_from_60m(bars.iloc[:-1], MARKET).empty


def test_weekly_aggregation_keeps_complete_exchange_week_only() -> None:
    import exchange_calendars as calendars

    sessions = calendars.get_calendar(MARKET["calendar_name"]).sessions_in_range("2026-01-05", "2026-01-09")
    daily = pd.DataFrame(
        {
            "open": np.arange(5.0) + 10,
            "high": np.arange(5.0) + 11,
            "low": np.arange(5.0) + 9,
            "close": np.arange(5.0) + 10.5,
            "volume": np.full(5, 100),
        },
        index=pd.DatetimeIndex(sessions).tz_localize(None) + pd.Timedelta("15h"),
    )
    weekly = aggregate_weekly_from_daily(daily, MARKET)
    assert len(weekly) == 1
    assert weekly.iloc[0]["open"] == 10
    assert weekly.iloc[0]["high"] == 15
    assert weekly.iloc[0]["low"] == 9
    assert weekly.iloc[0]["close"] == 14.5
    assert aggregate_weekly_from_daily(daily.iloc[:-1], MARKET).empty


def test_adjusted_indicator_track_keeps_raw_execution_track() -> None:
    times = pd.to_datetime(["2026-01-05 10:30", "2026-01-05 11:30"])
    raw_daily = pd.DataFrame({"close": [100.0]}, index=pd.to_datetime(["2026-01-05 15:00"]))
    qfq_daily = pd.DataFrame({"close": [80.0]}, index=raw_daily.index)
    intraday = pd.DataFrame(
        {"open": [100.0, 101.0], "high": [102.0, 102.0], "low": [99.0, 100.0], "close": [101.0, 101.0], "volume": [1, 1]},
        index=times,
    )
    result = apply_adjustment_factor(intraday, raw_daily, qfq_daily)
    np.testing.assert_allclose(result["close_raw"].to_numpy(), [101, 101])
    np.testing.assert_allclose(result["close_qfq"].to_numpy(), [80.8, 80.8])


def test_normalize_provider_chinese_columns() -> None:
    frame = pd.DataFrame({"日期": ["2026-01-05"], "开盘": [1], "最高": [2], "最低": [0.5], "收盘": [1.5], "成交量": [100]})
    result = normalize_bars(frame)
    assert list(result.columns) == ["open", "high", "low", "close", "volume"]
    assert result.index[0] == pd.Timestamp("2026-01-05")


def test_daily_provider_timestamps_are_at_configured_close() -> None:
    frame = pd.DataFrame(
        {"open": [10], "high": [11], "low": [9], "close": [10], "volume": [100]},
        index=pd.DatetimeIndex(["2026-01-05"]),
    )
    result = _at_daily_close(frame, MARKET)
    assert result.index[0] == pd.Timestamp("2026-01-05 15:00")


def test_resume_first_bar_is_unavailable_until_its_close() -> None:
    index = pd.to_datetime(["2026-01-05 10:30", "2026-01-07 10:30", "2026-01-07 11:30"])
    bars = pd.DataFrame(
        {"open": [10, 11, 12], "high": [11, 12, 13], "low": [9, 10, 11], "close": [10, 11, 12], "volume": [1, 1, 1]},
        index=index,
    )
    before_close = annotate_intraday_status(bars, MARKET, now=pd.Timestamp("2026-01-07 10:29"))
    assert not before_close.loc[index[1], "is_closed"]
    assert before_close.loc[index[1], "is_resume_first_bar"]
    after_close = annotate_intraday_status(bars, MARKET, now=pd.Timestamp("2026-01-07 10:31"))
    assert after_close.loc[index[1], "is_closed"]
    assert after_close.loc[index[1], "is_resume_first_bar"]


def test_market_limit_lot_and_t_plus_one_rules_are_configured() -> None:
    assert price_limits(10, "600519.SH", MARKET) == (9.0, 11.0)
    assert price_limits(10, "300750.SZ", MARKET) == (8.0, 12.0)
    assert price_limits(10, "600519.SH", MARKET, is_st=True) == (9.5, 10.5)
    assert round_to_lot(299, MARKET) == 200
    assert not can_sell(pd.Timestamp("2026-01-05").date(), pd.Timestamp("2026-01-05").date(), MARKET)
    assert can_sell(pd.Timestamp("2026-01-05").date(), pd.Timestamp("2026-01-06").date(), MARKET)
