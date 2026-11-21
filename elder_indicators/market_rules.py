from datetime import date, datetime, time
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Any


def board_key(symbol: str, market: dict[str, Any], *, is_st: bool = False) -> str:
    if is_st:
        return "st"
    code = symbol.split(".", 1)[0]
    for key, prefixes in market["board_code_prefixes"].items():
        if any(code.startswith(prefix) for prefix in prefixes):
            return key
    raise ValueError(f"No configured board classification for {symbol}")


def round_to_tick(price: float, market: dict[str, Any]) -> float:
    tick = Decimal(str(market["price_tick"]))
    value = (Decimal(str(price)) / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick
    return float(value)


def price_limits(
    previous_close: float,
    symbol: str,
    market: dict[str, Any],
    *,
    is_st: bool = False,
) -> tuple[float, float]:
    key = board_key(symbol, market, is_st=is_st)
    change = Decimal(str(market["board_limit_pct"][key]))
    lower = round_to_tick(float(Decimal(str(previous_close)) * (1 - change)), market)
    upper = round_to_tick(float(Decimal(str(previous_close)) * (1 + change)), market)
    return lower, upper


def round_to_lot(shares: int, market: dict[str, Any]) -> int:
    lot = int(market["min_lot"])
    return max(0, shares // lot * lot)


def can_sell(
    buy_date: date,
    sell_date: date,
    market: dict[str, Any],
) -> bool:
    return not bool(market["t_plus_1"]) or sell_date > buy_date


def is_session_close(value: datetime, market: dict[str, Any]) -> bool:
    sessions = market["trading_sessions"]
    clock = value.time().replace(tzinfo=None)
    return any(
        time.fromisoformat(sessions[key]) == clock
        for key in ("morning_close", "afternoon_close")
    )


def is_within_trading_session(value: datetime, market: dict[str, Any]) -> bool:
    sessions = market["trading_sessions"]
    clock = value.time().replace(tzinfo=None)
    return any(
        time.fromisoformat(sessions[start]) <= clock <= time.fromisoformat(sessions[end])
        for start, end in (("morning_open", "morning_close"), ("afternoon_open", "afternoon_close"))
    )
