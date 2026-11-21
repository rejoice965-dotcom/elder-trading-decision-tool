import ast
import json
from pathlib import Path

import exchange_calendars as calendars
import numpy as np
import pandas as pd

from elder_indicators.config import load_config
from elder_indicators.market_rules import can_sell
from market_data.bars import aggregate_daily_from_60m, aggregate_weekly_from_daily
from market_data.provider import load_cached
from presentation.dashboard import build_daily_view, build_markers


ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(ROOT / "docs" / "indicators.yaml")
MARKET = CONFIG["market"]
SYMBOL = "600519.SH"


def main() -> None:
    cache_dir = ROOT / MARKET["cache"]["directory"]
    bundle = load_cached(SYMBOL, cache_dir)
    qfq_daily = bundle.daily_qfq
    raw_daily = bundle.daily_raw
    qfq_intraday = bundle.intraday_qfq
    raw_intraday = bundle.intraday_raw
    signals = pd.read_csv(ROOT / "examples/signals.csv", parse_dates=["timestamp"])

    daily_factor = qfq_daily["close"].div(raw_daily["close"])
    assert qfq_daily.index.equals(raw_daily.index)
    assert qfq_intraday.index.equals(raw_intraday.index)
    expected_factor = pd.Series(qfq_intraday.index.date, index=qfq_intraday.index).map(
        pd.Series(daily_factor.to_numpy(), index=qfq_daily.index.date)
    )
    assert np.isfinite(daily_factor).all() and daily_factor.gt(0).all()
    columns = ["open", "high", "low", "close"]
    raw_track = qfq_intraday[[f"{column}_raw" for column in columns]].set_axis(columns, axis=1)
    qfq_track = qfq_intraday[[f"{column}_qfq" for column in columns]].set_axis(columns, axis=1)
    np.testing.assert_allclose(raw_track, raw_intraday[columns], rtol=0, atol=1e-10)
    factor_error = (qfq_track - raw_track.mul(expected_factor, axis=0)).abs()
    assert factor_error.notna().all().all() and factor_error.to_numpy().max() < 1e-10
    raw_returns = raw_daily["close"].pct_change()
    qfq_returns = qfq_daily["close"].pct_change()
    # The threshold separates material factor changes from price rounding noise.
    factor_change = daily_factor.pct_change().abs().gt(0.001)
    last_factor_change = None
    if factor_change.any():
        example_date = factor_change[factor_change].index[-1]
        last_factor_change = {
            "date": str(example_date.date()),
            "raw_return_pct": round(float(raw_returns.loc[example_date] * 100), 4),
            "qfq_return_pct": round(float(qfq_returns.loc[example_date] * 100), 4),
        }

    calendar = calendars.get_calendar(MARKET["calendar_name"])
    expected_sessions = calendar.sessions_in_range(
        qfq_daily.index.min().normalize(), qfq_daily.index.max().normalize()
    )
    expected_dates = set(pd.DatetimeIndex(expected_sessions).tz_localize(None).date)
    daily_dates = set(qfq_daily.index.date)
    missing_sessions = expected_dates - daily_dates
    assert daily_dates.issubset(expected_dates)
    signal_dates = set(signals["timestamp"].dt.date)
    assert signals["timestamp"].isin(raw_intraday.index).all()
    signal_days = signals["timestamp"].dt.normalize()
    previous_raw = raw_daily.set_axis(raw_daily.index.normalize()).shift(1)
    values = pd.DataFrame(signals["indicator_values"].map(ast.literal_eval).tolist())
    for field in ("high", "low", "close"):
        signal_field = "previous_close_raw" if field == "close" else f"previous_day_{field}_raw"
        np.testing.assert_array_equal(values[signal_field], previous_raw.loc[signal_days, field])
    intraday_dates = set(raw_intraday.index.date)
    assert signal_dates.issubset(intraday_dates)
    assert not signal_dates.intersection(missing_sessions)

    counts_by_day = raw_intraday.groupby(raw_intraday.index.date).size()
    expected_clocks = tuple(MARKET["intraday_bar_close_times"])
    observed_clocks = raw_intraday.groupby(raw_intraday.index.date).apply(
        lambda day: tuple(day.index.strftime("%H:%M"))
    )
    full_days = counts_by_day.eq(int(MARKET["intraday_bars_per_day"]))
    assert observed_clocks.loc[full_days].map(lambda clocks: clocks == expected_clocks).all()
    assert observed_clocks.map(lambda clocks: set(clocks).issubset(expected_clocks)).all()
    assert intraday_dates.issubset(expected_dates)
    partial_days = counts_by_day.loc[~full_days]
    daily_from_60m = aggregate_daily_from_60m(qfq_intraday, MARKET)
    daily_common = daily_from_60m.index.intersection(qfq_daily.index)
    close_error = (daily_from_60m.loc[daily_common, "close"] - qfq_daily.loc[daily_common, "close"]).abs()
    weekly_from_daily = aggregate_weekly_from_daily(qfq_daily, MARKET)
    assert len(daily_from_60m) == int(full_days.sum())
    assert len(daily_common) == len(daily_from_60m) and close_error.max() < 1e-10
    weekly_reference = qfq_daily.groupby(pd.Grouper(freq="W-FRI")).agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"),
    )
    session_counts = pd.Series(1, index=pd.DatetimeIndex(expected_sessions).tz_localize(None))
    cached_counts = qfq_daily["close"].resample("W-FRI").size()
    expected_counts = session_counts.resample("W-FRI").sum()
    complete_weeks = cached_counts.eq(expected_counts) & cached_counts.gt(0)
    weekly_reference = weekly_reference.loc[complete_weeks]
    labels = weekly_from_daily.index.to_period("W-FRI").end_time.normalize()
    assert labels.equals(pd.DatetimeIndex(weekly_reference.index, name=labels.name))
    np.testing.assert_allclose(weekly_from_daily, weekly_reference, rtol=0, atol=1e-10)

    _, factors, limits, _ = build_daily_view(qfq_daily, raw_daily, MARKET, SYMBOL)
    markers = build_markers(signals, factors, limits, market=MARKET)
    possible_not_filled = sum(marker["possible_execution_warning"] for marker in markers)
    at_limit_entries = int(values["at_price_limit"].sum())

    first_signal_day = signals["timestamp"].min().date()
    t_plus_one_same_day_sell_allowed = can_sell(first_signal_day, first_signal_day, MARKET)
    next_session = calendar.sessions_in_range(
        pd.Timestamp(first_signal_day) + pd.Timedelta("1D"),
        pd.Timestamp(first_signal_day) + pd.Timedelta("14D"),
    )[0]
    next_day = pd.Timestamp(next_session).tz_localize(None).date()
    t_plus_one_next_day_sell_allowed = can_sell(first_signal_day, next_day, MARKET)
    assert not t_plus_one_same_day_sell_allowed
    assert t_plus_one_next_day_sell_allowed

    print(json.dumps({
        "adjustment_tracks": {
            "daily_rows_aligned": len(qfq_daily.index.intersection(raw_daily.index)),
            "daily_qfq_raw_factor_min": float(daily_factor.min()),
            "daily_qfq_raw_factor_max": float(daily_factor.max()),
            "intraday_ohlc_mapping_max_abs_error": float(factor_error.to_numpy().max()),
            "intraday_qfq_rows_checked": len(qfq_intraday),
            "material_factor_change_days": int(factor_change.sum()),
            "last_factor_change": last_factor_change,
        },
        "suspensions_and_signals": {
            "calendar": MARKET["calendar_name"],
            "expected_sessions": len(expected_dates),
            "cached_daily_sessions": len(daily_dates),
            "missing_sessions_in_daily_cache": len(missing_sessions),
            "signals": len(signals),
            "signals_with_exact_t_minus_one_raw_references": len(values),
            "signal_dates_without_intraday": len(signal_dates - intraday_dates),
            "signals_on_missing_sessions": len(signal_dates & missing_sessions),
        },
        "bar_construction": {
            "configured_intraday_bars_per_day": MARKET["intraday_bars_per_day"],
            "intraday_bar_count_distribution": {str(key): int(value) for key, value in counts_by_day.value_counts().sort_index().items()},
            "complete_session_close_times": list(expected_clocks),
            "complete_intraday_sessions": int(full_days.sum()),
            "partial_source_sessions": {str(index): int(value) for index, value in partial_days.items()},
            "daily_bars_aggregated_from_60m": len(daily_from_60m),
            "aggregated_vs_downloaded_daily_close_max_abs_error": float(close_error.max()),
            "weekly_bars_aggregated_from_daily": len(weekly_from_daily),
        },
        "a_share_execution_rules": {
            "cash_only": MARKET["cash_only"],
            "allow_short": MARKET["allow_short"],
            "same_day_sell_allowed": t_plus_one_same_day_sell_allowed,
            "next_trading_day": next_day.isoformat(),
            "next_day_sell_allowed": t_plus_one_next_day_sell_allowed,
            "signals_marked_possible_unfilled": possible_not_filled,
            "signal_candidate_prices_at_limit": at_limit_entries,
            "historical_st_status_available": "is_st" in raw_daily,
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
