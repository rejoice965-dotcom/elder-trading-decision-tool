from __future__ import annotations

import ast
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from elder_indicators.market_rules import board_key, price_limits


PROVENANCE = "依据：公开资料交叉核对，非原书直引"
DISCLAIMER = "仅供研究与回测，不构成投资建议"


def calculate_display_indicators(
    daily_qfq: pd.DataFrame,
    params: dict[str, Any],
) -> pd.DataFrame:
    """Calculate chart-only series. This function does not create or filter signals."""
    close = daily_qfq["close"]
    ema_period = int(params["ema_period"])
    fast = int(params["macd_fast"])
    slow = int(params["macd_slow"])
    macd_signal = int(params["macd_signal"])
    fi_period = int(params["fi_ema"])
    rsi_period = int(params["rsi_period"])

    ema = close.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
    fast_ema = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
    slow_ema = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd = fast_ema - slow_ema
    macd_average = macd.ewm(span=macd_signal, adjust=False, min_periods=macd_signal).mean()
    histogram = macd - macd_average
    force_raw = close.diff() * daily_qfq["volume"]
    force_index = force_raw.ewm(span=fi_period, adjust=False, min_periods=fi_period).mean()
    bull_power = daily_qfq["high"] - ema
    bear_power = daily_qfq["low"] - ema
    delta = close.diff()
    average_gain = delta.clip(lower=0).ewm(
        alpha=1 / rsi_period, adjust=False, min_periods=rsi_period
    ).mean()
    average_loss = -delta.clip(upper=0).ewm(
        alpha=1 / rsi_period, adjust=False, min_periods=rsi_period
    ).mean()
    relative_strength = average_gain / average_loss
    rsi = 100 - 100 / (1 + relative_strength)
    rsi = rsi.mask(average_loss.eq(0) & average_gain.gt(0), 100)
    rsi = rsi.mask(average_gain.eq(0) & average_loss.gt(0), 0)
    rsi = rsi.mask(average_gain.eq(0) & average_loss.eq(0), 50)

    return pd.DataFrame(
        {
            "ema": ema,
            "macd": macd,
            "macd_signal": macd_average,
            "macd_histogram": histogram,
            "force_index": force_index,
            "bull_power": bull_power,
            "bear_power": bear_power,
            "rsi": rsi,
        },
        index=daily_qfq.index,
    ).replace([np.inf, -np.inf], np.nan)


def _date_key(value: Any) -> date:
    return pd.Timestamp(value).date()


def build_daily_view(
    daily_qfq: pd.DataFrame,
    daily_raw: pd.DataFrame,
    market: dict[str, Any],
    symbol: str,
) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, dict[str, Any]], dict[str, Any]]:
    qfq_by_date = {_date_key(index): row for index, row in daily_qfq.iterrows()}
    raw_by_date = {_date_key(index): row for index, row in daily_raw.iterrows()}
    if not qfq_by_date or not raw_by_date:
        raise ValueError("Daily qfq and raw cache files must contain rows")

    calendar = __import__("exchange_calendars").get_calendar(market["calendar_name"])
    first_day = min(qfq_by_date)
    last_day = max(qfq_by_date)
    sessions = calendar.sessions_in_range(pd.Timestamp(first_day), pd.Timestamp(last_day))
    session_dates = pd.DatetimeIndex(sessions).tz_localize(None).date

    board = board_key(symbol, market)
    has_historical_st = "is_st" in daily_raw.columns
    chart_rows: list[dict[str, Any]] = []
    factor_by_date: dict[str, float] = {}
    limit_by_date: dict[str, dict[str, Any]] = {}
    suspension_dates: list[str] = []
    previous_close: float | None = None

    for session in session_dates:
        key = session.isoformat()
        qfq_row = qfq_by_date.get(session)
        raw_row = raw_by_date.get(session)
        if qfq_row is None or raw_row is None:
            chart_rows.append({"time": key})
            if market["skip_suspended"]:
                suspension_dates.append(key)
            continue

        raw_close = float(raw_row["close"])
        qfq_close = float(qfq_row["close"])
        factor = qfq_close / raw_close if raw_close else 1.0
        factor_by_date[key] = factor
        if previous_close is None:
            previous_close = float(raw_row["close"])
            limits = None
        else:
            is_st = bool(raw_row["is_st"]) if has_historical_st and pd.notna(raw_row["is_st"]) else False
            lower, upper = price_limits(
                previous_close,
                symbol,
                market,
                is_st=is_st,
            )
            touched_upper = float(raw_row["high"]) >= upper
            touched_lower = float(raw_row["low"]) <= lower
            limits = {
                "upper": upper,
                "lower": lower,
                "touched_upper": touched_upper,
                "touched_lower": touched_lower,
                "touched": touched_upper or touched_lower,
                "is_st": is_st if has_historical_st else None,
                "board": "ST" if is_st else board,
                "status_source": "historical ST field" if has_historical_st else "board threshold; historical ST status unavailable",
            }
            limit_by_date[key] = limits

        chart_rows.append(
            {
                "time": key,
                "open": float(qfq_row["open"]),
                "high": float(qfq_row["high"]),
                "low": float(qfq_row["low"]),
                "close": qfq_close,
            }
        )
        previous_close = raw_close

    daily_last = daily_raw.sort_index().iloc[-1]
    daily_previous = daily_raw.sort_index().iloc[-2] if len(daily_raw) > 1 else daily_last
    last_date = _date_key(daily_raw.sort_index().index[-1]).isoformat()
    latest_limits = limit_by_date.get(last_date)
    summary = {
        "symbol": symbol,
        "name": symbol,
        "last_date": last_date,
        "last_raw_close": float(daily_last["close"]),
        "change_pct": (
            (float(daily_last["close"]) / float(daily_previous["close"]) - 1) * 100
            if float(daily_previous["close"])
            else 0.0
        ),
        "limit_status": latest_limits,
        "historical_st_available": has_historical_st,
        "board": board,
        "suspension_dates": suspension_dates,
        "daily_range": [min(qfq_by_date).isoformat(), max(qfq_by_date).isoformat()],
    }
    return chart_rows, factor_by_date, limit_by_date, summary


def _signal_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    parsed = ast.literal_eval(str(value))
    if not isinstance(parsed, dict):
        raise ValueError("signals.csv indicator_values must contain a mapping")
    return parsed


def build_markers(
    signals: pd.DataFrame,
    factor_by_date: dict[str, float],
    limit_by_date: dict[str, dict[str, Any]],
    *,
    market: dict[str, Any],
    book_confirmations: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    markers = []
    for index, row in signals.reset_index(drop=True).iterrows():
        day = pd.Timestamp(row["timestamp"]).date().isoformat()
        if day not in factor_by_date:
            raise ValueError(
                f"Signal {row['rule_id']} on {day} has no matching daily K-line"
            )
        values = _signal_dict(row["indicator_values"])
        date_limits = limit_by_date.get(day)
        touched_limit = bool(values.get("at_price_limit", False)) or bool(
            date_limits and date_limits["touched"]
        )
        side = str(row["side"])
        confirmation = (book_confirmations or {}).get(str(row["rule_id"]))
        book_note = None
        if confirmation:
            chapters = "；".join(confirmation["book_chapter"])
            pages = "、".join(
                f"第{page.removeprefix('p.')}页"
                for page in confirmation["book_page"]
            )
            book_note = (
                f"书内确认：《以交易为生》（原书第2版）"
                f"{chapters} {pages}"
            )
        stop_key = "previous_day_low_raw" if side == "BUY" else "previous_day_high_raw"
        entry = float(row["price"])
        stop = values.get(stop_key)
        markers.append(
            {
                "id": int(index + 1),
                "time": day,
                "timestamp": pd.Timestamp(row["timestamp"]).isoformat(sep=" "),
                "side": side,
                "price_raw": entry,
                "price_qfq": entry * factor_by_date[day],
                "rule_id": str(row["rule_id"]),
                "book_confirmation": book_note,
                "trigger_rule": (
                    "前一交易日高点上方突破买入止损单"
                    if side == "BUY"
                    else "前一交易日低点下方突破卖出止损单"
                ),
                "source_quote": str(row["source_quote"]),
                "source_url": str(row["source_url"]),
                "confidence": str(row["confidence"]),
                "indicator_values": values,
                "stop_loss_raw": float(stop) if stop is not None and pd.notna(stop) else None,
                "possible_execution_warning": touched_limit,
                "limit_status": date_limits,
                "entry_allowed": bool(values.get("entry_allowed", False)),
                "short_entry_allowed": bool(values.get("short_entry_allowed", False)),
            }
        )
    return markers


def build_payload(
    daily_qfq: pd.DataFrame,
    daily_raw: pd.DataFrame,
    signals: pd.DataFrame,
    *,
    params: dict[str, Any],
    market: dict[str, Any],
    symbol: str,
    book_confirmations: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows, factors, limits, summary = build_daily_view(daily_qfq, daily_raw, market, symbol)
    indicators = calculate_display_indicators(daily_qfq, params)
    indicator_rows = [
        {
            "time": _date_key(index).isoformat(),
            **{
                name: float(value) if pd.notna(value) else None
                for name, value in series.items()
            },
        }
        for index, series in indicators.iterrows()
    ]
    metadata = {
        "risk_pct": float(params["risk_per_trade"]),
        "ema_period": int(params["ema_period"]),
        "macd_fast": int(params["macd_fast"]),
        "macd_slow": int(params["macd_slow"]),
        "macd_signal": int(params["macd_signal"]),
        "fi_ema": int(params["fi_ema"]),
        "rsi_period": int(params["rsi_period"]),
        "oversold": float(params["oversold"]),
        "overbought": float(params["overbought"]),
        "price_tick": float(market["price_tick"]),
        "minimum_lot": int(market["min_lot"]),
        "allow_short": bool(market["allow_short"]),
        "board_limit_pct": market["board_limit_pct"],
        "board_code_prefixes": market["board_code_prefixes"],
        "trading_calendar": market["calendar_name"],
        "historical_st_available": summary["historical_st_available"],
        "provenance": PROVENANCE,
        "disclaimer": DISCLAIMER,
    }
    return {
        "summary": summary,
        "candles": rows,
        "indicators": indicator_rows,
        "markers": build_markers(
            signals,
            factors,
            limits,
            market=market,
            book_confirmations=book_confirmations,
        ),
        "config": metadata,
        "provenance": PROVENANCE,
        "disclaimer": DISCLAIMER,
    }


def estimate_position(
    equity: float | None,
    entry: float,
    stop: float | None,
    *,
    risk_pct: float,
    minimum_lot: int,
    allow_short: bool,
    side: str,
) -> dict[str, Any]:
    if equity is None or not np.isfinite(equity) or equity <= 0:
        return {"shares": None, "risk_budget": None, "message": "请填写有效的账户权益以估算仓位。"}
    if side == "SELL" and not allow_short:
        return {"shares": 0, "risk_budget": equity * risk_pct, "message": "A 股配置已关闭做空，卖出信号不可作为开空仓位。"}
    if stop is None or not np.isfinite(stop):
        return {"shares": None, "risk_budget": equity * risk_pct, "message": "该信号缺少止损参考价，无法估算仓位。"}
    distance = abs(entry - stop)
    if distance <= 0:
        return {"shares": 0, "risk_budget": equity * risk_pct, "message": "止损距离为零，无法估算仓位。"}
    raw_shares = int(np.floor(equity * risk_pct / distance))
    shares = raw_shares // minimum_lot * minimum_lot
    return {
        "shares": shares,
        "risk_budget": equity * risk_pct,
        "distance": distance,
        "message": "按权益风险预算和整手规则估算，不代表实际成交。",
    }
