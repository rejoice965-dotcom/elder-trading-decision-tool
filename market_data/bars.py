from datetime import timedelta
from typing import Any

import pandas as pd


OHLCV = ["open", "high", "low", "close", "volume"]


def normalize_bars(frame: pd.DataFrame, *, timestamp_column: str | None = None) -> pd.DataFrame:
    aliases = {
        "日期": "timestamp",
        "时间": "timestamp",
        "日期时间": "timestamp",
        "date": "timestamp",
        "datetime": "timestamp",
        "day": "timestamp",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "成交额": "amount",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "amount": "amount",
    }
    result = frame.rename(columns={column: aliases.get(column, column) for column in frame.columns}).copy()
    if timestamp_column:
        result = result.rename(columns={timestamp_column: "timestamp"})
    if "timestamp" not in result:
        if isinstance(result.index, pd.DatetimeIndex):
            result = result.rename_axis("timestamp").reset_index()
        else:
            raise ValueError("A timestamp column or DatetimeIndex is required")
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="coerce")
    for column in OHLCV:
        if column not in result:
            raise ValueError(f"Missing required OHLCV field: {column}")
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.dropna(subset=["timestamp", "open", "high", "low", "close"])
    return result.sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")


def apply_adjustment_factor(
    intraday_raw: pd.DataFrame,
    daily_raw: pd.DataFrame,
    daily_qfq: pd.DataFrame,
) -> pd.DataFrame:
    raw_daily = daily_raw["close"].groupby(daily_raw.index.date).last()
    qfq_daily = daily_qfq["close"].groupby(daily_qfq.index.date).last()
    factors = qfq_daily.div(raw_daily).replace([float("inf"), -float("inf")], pd.NA)
    result = intraday_raw.copy()
    factor = pd.Series(result.index.date, index=result.index).map(factors)
    for column in OHLCV[:4]:
        result[f"{column}_raw"] = result[column]
        result[f"{column}_qfq"] = result[column] * factor.to_numpy()
    result["volume_qfq"] = result["volume"]
    return result.dropna(subset=["close_qfq"])


def aggregate_daily_from_60m(
    bars: pd.DataFrame,
    market: dict[str, Any],
) -> pd.DataFrame:
    expected = int(market["intraday_bars_per_day"])
    dates = pd.Series(bars.index.date, index=bars.index, name="session_date")
    grouped = bars.groupby(dates)
    daily = grouped.agg(
        open=("open_qfq", "first") if "open_qfq" in bars else ("open", "first"),
        high=("high_qfq", "max") if "high_qfq" in bars else ("high", "max"),
        low=("low_qfq", "min") if "low_qfq" in bars else ("low", "min"),
        close=("close_qfq", "last") if "close_qfq" in bars else ("close", "last"),
        volume=("volume", "sum"),
        bar_count=("close", "count"),
    )
    daily = daily.loc[daily["bar_count"].eq(expected)].drop(columns="bar_count")
    daily.index = pd.to_datetime(daily.index) + pd.Timedelta("15h")
    return daily


def aggregate_weekly_from_daily(
    daily: pd.DataFrame,
    market: dict[str, Any],
) -> pd.DataFrame:
    if "is_closed" in daily:
        daily = daily.loc[daily["is_closed"].fillna(False)].copy()
    if daily.empty:
        return pd.DataFrame(columns=OHLCV, index=pd.DatetimeIndex([], name="timestamp"))
    calendar_name = market["calendar_name"]
    try:
        import exchange_calendars as exchange_calendars
    except ImportError as exc:
        raise RuntimeError("exchange-calendars is required for complete trading-week aggregation") from exc
    calendar = exchange_calendars.get_calendar(calendar_name)
    first_date = pd.Timestamp(daily.index.min().date())
    last_date = pd.Timestamp(daily.index.max().date())
    weekdays = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
    week_start_day = weekdays.index(market["week_starting_day"])
    week_end_day = weekdays.index(market["week_ending_day"])
    start_offset = (first_date.weekday() - week_start_day) % len(weekdays)
    end_offset = (week_end_day - last_date.weekday()) % len(weekdays)
    start = first_date - pd.Timedelta(f"{start_offset}D")
    end = last_date + pd.Timedelta(f"{end_offset}D")
    all_sessions = pd.DatetimeIndex(calendar.sessions)
    session_labels = all_sessions.tz_localize(None)
    session_mask = (session_labels.date >= start.date()) & (session_labels.date <= end.date())
    session_dates = list(session_labels[session_mask].date)
    session_frame = pd.DataFrame({"session_date": session_dates}, index=session_labels[session_mask])
    session_frame["week_start"] = session_frame["session_date"].map(
        lambda value: value - timedelta(days=(value.weekday() - week_start_day) % len(weekdays))
    )
    available_dates = set(daily.index.date)
    expected_by_week = session_frame.groupby("week_start")["session_date"].agg(list)
    complete_dates = {
        trading_date
        for week_dates in expected_by_week
        if set(week_dates).issubset(available_dates)
        for trading_date in week_dates
    }
    complete = daily.loc[[stamp.date() in complete_dates for stamp in daily.index]]
    if complete.empty:
        return pd.DataFrame(columns=OHLCV, index=pd.DatetimeIndex([], name="timestamp"))
    week_key = pd.Series(
        [stamp.date() - timedelta(days=(stamp.weekday() - week_start_day) % len(weekdays)) for stamp in complete.index],
        index=complete.index,
        name="week_start",
    )
    weekly = complete.groupby(week_key).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    last_dates = complete.groupby(week_key).apply(lambda frame: frame.index.max())
    weekly.index = pd.DatetimeIndex(last_dates.to_list(), name="timestamp")
    return weekly.sort_index()


def annotate_intraday_status(
    bars: pd.DataFrame,
    market: dict[str, Any],
    *,
    now: pd.Timestamp | None = None,
) -> pd.DataFrame:
    now = pd.Timestamp.now() if now is None else pd.Timestamp(now)
    result = bars.copy()
    close_times = set(market["intraday_bar_close_times"])
    result["is_closed"] = [
        stamp.date() < now.date()
        or (
            stamp.date() == now.date()
            and stamp.strftime("%H:%M") in close_times
            and stamp <= now
        )
        for stamp in result.index
    ]

    calendar = __import__("exchange_calendars").get_calendar(market["calendar_name"])
    sessions = calendar.sessions_in_range(
        pd.Timestamp(result.index.min().date()), pd.Timestamp(result.index.max().date())
    ) if not result.empty else []
    session_labels = pd.DatetimeIndex(sessions).tz_localize(None)
    expected = pd.Series(list(session_labels.date), index=session_labels)
    observed = set(result.index.date)
    suspended_sessions = set(expected.to_list()) - observed
    resume_dates = set()
    for session in expected:
        if session in observed:
            if session - pd.Timedelta("1D") in suspended_sessions:
                resume_dates.add(session)
    result["is_resume_first_bar"] = pd.Series(result.index.date, index=result.index).isin(resume_dates)
    return result
