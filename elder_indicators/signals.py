from typing import Any

import numpy as np
import pandas as pd

from .indicators import calculate_indicators
from .market_rules import board_key


SOURCE_URLS = {
    "S1": "https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf",
    "S2": "https://www.marketsfn.com/book/trading-for-a-living",
    "S3": "https://forestbergen.com/portfolio-item/join-dr-alexander-elder-in-his-trading-room",
    "S5": "https://aloycwl.blogspot.com/2022/03/trading-for-living-alexander-elder-1993.html",
}


def _closed_only(frame: pd.DataFrame) -> pd.DataFrame:
    if "is_closed" in frame:
        return frame.loc[frame["is_closed"].fillna(False)].copy()
    return frame.copy()


def _available(frame: pd.DataFrame) -> pd.DataFrame:
    if "is_suspended" in frame:
        return frame.loc[~frame["is_suspended"].fillna(False)].copy()
    if "volume" in frame:
        return frame.loc[frame["volume"].fillna(0).gt(0)].copy()
    return frame.copy()


def _screen_one(weekly: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
    indicator_values = calculate_indicators(weekly, params)
    result = weekly[["close"]].copy()
    result["ema_slope"] = indicator_values["ema"].diff()
    result["histogram_slope"] = indicator_values["histogram"].diff()
    long_direction = result["ema_slope"].gt(0) & result["histogram_slope"].gt(0)
    short_direction = result["ema_slope"].lt(0) & result["histogram_slope"].lt(0)
    result["direction"] = 0
    result.loc[long_direction, "direction"] = 1
    result.loc[short_direction, "direction"] = -1
    return result[["direction", "ema_slope", "histogram_slope"]].reset_index(names="timestamp")


def _screen_two(daily: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
    values = calculate_indicators(daily, params)
    oversold = float(params["oversold"])
    overbought = float(params["overbought"])
    long_setup = (
        (values["bear_power"].lt(0) & values["bear_power"].gt(values["bear_power"].shift(1)))
        | values["stoch_k"].le(oversold)
        | values["rsi"].le(oversold)
    )
    short_setup = (
        (values["bull_power"].gt(0) & values["bull_power"].lt(values["bull_power"].shift(1)))
        | values["stoch_k"].ge(overbought)
        | values["rsi"].ge(overbought)
    )
    result = daily[["high", "low", "close"]].copy()
    raw_high = daily["high_raw"] if "high_raw" in daily else daily["high"]
    raw_low = daily["low_raw"] if "low_raw" in daily else daily["low"]
    raw_close = daily["close_raw"] if "close_raw" in daily else daily["close"]
    result["previous_high"] = raw_high
    result["previous_low"] = raw_low
    result["previous_close_raw"] = raw_close
    if "is_st" in daily:
        result["is_st"] = daily["is_st"].fillna(False).astype(bool)
    result["long_setup"] = long_setup
    result["short_setup"] = short_setup
    for name in ("force_index", "bull_power", "bear_power", "stoch_k", "stoch_d", "rsi", "volume"):
        result[name] = values[name]
    return result.reset_index(names="timestamp")


def build_triple_screen_signals(
    weekly: pd.DataFrame,
    daily: pd.DataFrame,
    intraday: pd.DataFrame,
    *,
    symbol: str,
    params: dict[str, Any],
    market: dict[str, Any],
) -> pd.DataFrame:
    """Create traceable A-share signals from closed weekly, daily, and 60-minute bars.

    Frames use a DatetimeIndex and separate adjusted OHLCV (`*_qfq`) from raw execution
    OHLCV (`*_raw`). If suffixed columns are absent, the input OHLCV is used for both.
    """
    required = {"open", "high", "low", "close", "volume"}
    for frame in (weekly, daily, intraday):
        if not required.issubset(frame.columns):
            raise ValueError(f"OHLCV columns required: {sorted(required)}")

    weekly = _available(_closed_only(weekly)).sort_index()
    daily = _available(_closed_only(daily)).sort_index()
    intraday = _available(_closed_only(intraday)).sort_index()
    if weekly.empty or daily.empty or intraday.empty:
        return pd.DataFrame(columns=_signal_columns())

    directions = _screen_one(weekly, params)
    daily_screens = _screen_two(daily, params)
    daily_screens = pd.merge_asof(
        daily_screens.sort_values("timestamp"),
        directions.sort_values("timestamp"),
        on="timestamp",
        direction="backward",
        allow_exact_matches=True,
    )
    low = intraday.reset_index(names="timestamp").sort_values("timestamp")
    raw_open = "open_raw" if "open_raw" in low else "open"
    raw_high = "high_raw" if "high_raw" in low else "high"
    raw_low = "low_raw" if "low_raw" in low else "low"
    raw_close = "close_raw" if "close_raw" in low else "close"
    low["session_date"] = low["timestamp"].dt.normalize()
    if market["resume_signal_policy"]["first_60m_bar_must_be_closed"]:
        if "is_closed" in low:
            low = low.loc[low["is_closed"].fillna(False)].copy()

    # The latest eligible daily row already represents T-1 for the intraday session.
    daily_screens["session_date"] = daily_screens["timestamp"].dt.normalize()
    aligned = pd.merge_asof(
        low,
        daily_screens.drop(columns="timestamp"),
        on="session_date",
        direction="backward",
        allow_exact_matches=False,
        suffixes=("_low", "_mid"),
    )
    if aligned.empty:
        return pd.DataFrame(columns=_signal_columns())

    execution_open = raw_open if raw_open in aligned else f"{raw_open}_low"
    execution_high = raw_high if raw_high in aligned else f"{raw_high}_low"
    execution_low = raw_low if raw_low in aligned else f"{raw_low}_low"
    execution_close = raw_close if raw_close in aligned else f"{raw_close}_low"
    tick_offset = float(params["breakout_offset_ticks"]) * float(market["price_tick"])
    aligned["buy_stop_price_raw"] = aligned["previous_high"] + tick_offset
    aligned["sell_stop_price_raw"] = aligned["previous_low"] - tick_offset
    long_trigger = aligned["long_setup"] & aligned["direction"].eq(1)
    long_trigger &= aligned[execution_high].ge(aligned["buy_stop_price_raw"])
    short_trigger = aligned["short_setup"] & aligned["direction"].eq(-1)
    short_trigger &= aligned[execution_low].le(aligned["sell_stop_price_raw"])
    candidates = aligned.loc[long_trigger | short_trigger].copy()
    if candidates.empty:
        return pd.DataFrame(columns=_signal_columns())
    candidates["side"] = "BUY"
    candidates.loc[short_trigger.loc[candidates.index], "side"] = "SELL"

    selected_board = board_key(symbol, market)
    regular_limit = float(market["board_limit_pct"][selected_board])
    is_st = candidates.get("is_st", pd.Series(False, index=candidates.index)).fillna(False)
    limit_rate = is_st.map(
        lambda value: float(market["board_limit_pct"]["st"]) if value else regular_limit
    )
    tick = float(market["price_tick"])
    previous_close = candidates["previous_close_raw"]
    limit_up = np.floor(previous_close * (1 + limit_rate) / tick + 0.5) * tick
    limit_down = np.floor(previous_close * (1 - limit_rate) / tick + 0.5) * tick
    buy_candidate_price = candidates[[execution_open]].iloc[:, 0].where(
        candidates[execution_open].gt(candidates["buy_stop_price_raw"]),
        candidates["buy_stop_price_raw"],
    )
    sell_candidate_price = candidates[[execution_open]].iloc[:, 0].where(
        candidates[execution_open].lt(candidates["sell_stop_price_raw"]),
        candidates["sell_stop_price_raw"],
    )
    candidates["price"] = buy_candidate_price.where(
        candidates["side"].eq("BUY"), sell_candidate_price
    )
    at_upper_limit = candidates["price"].ge(limit_up)
    at_lower_limit = candidates["price"].le(limit_down)
    entry_allowed = candidates["side"].eq("BUY") & ~at_upper_limit
    candidates["rule_id"] = "SYS-05"
    candidates["indicator_values"] = candidates.apply(
        lambda row: {
            "direction": int(row["direction"]),
            "ema_slope": float(row["ema_slope"]),
            "histogram_slope": float(row["histogram_slope"]),
            "force_index": _number(row["force_index"]),
            "bull_power": _number(row["bull_power"]),
            "bear_power": _number(row["bear_power"]),
            "stoch_k": _number(row["stoch_k"]),
            "stoch_d": _number(row["stoch_d"]),
            "rsi": _number(row["rsi"]),
            "previous_day_high_raw": _number(row["previous_high"]),
            "previous_day_low_raw": _number(row["previous_low"]),
            "previous_close_raw": _number(row["previous_close_raw"]),
            "execution_price_raw": _number(row[execution_close]),
            "buy_stop_price_raw": _number(row["buy_stop_price_raw"]),
            "sell_stop_price_raw": _number(row["sell_stop_price_raw"]),
            "bar_high_raw": _number(row[execution_high]),
            "bar_low_raw": _number(row[execution_low]),
            "bar_open_raw": _number(row[execution_open]),
            "indicator_close_qfq": _number(row.get("close_qfq", row.get("close_mid"))),
            "price_limit_up_raw": _number(limit_up.loc[row.name]),
            "price_limit_down_raw": _number(limit_down.loc[row.name]),
            "at_price_limit": bool(at_upper_limit.loc[row.name] | at_lower_limit.loc[row.name]),
            "entry_allowed": bool(entry_allowed.loc[row.name]),
            "short_entry_allowed": bool(market["allow_short"] and not at_lower_limit.loc[row.name]),
        },
        axis=1,
    )
    candidates["timestamp"] = pd.to_datetime(candidates["timestamp"])
    candidates["symbol"] = symbol
    candidates["source_url"] = SOURCE_URLS["S1"]
    candidates["source_quote"] = "buy stop order to catch an upside breakout"
    candidates.loc[candidates["side"].eq("SELL"), "source_quote"] = (
        "sell short-term strength in downtrends"
    )
    candidates["confidence"] = "A"
    candidates["source_page"] = None
    return candidates[_signal_columns()].reset_index(drop=True)


def _number(value: Any) -> float | None:
    return None if pd.isna(value) else float(value)


def _signal_columns() -> list[str]:
    return [
        "timestamp",
        "symbol",
        "side",
        "price",
        "rule_id",
        "indicator_values",
        "source_url",
        "source_quote",
        "confidence",
        "source_page",
    ]
