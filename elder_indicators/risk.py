from datetime import date
from typing import Any

import pandas as pd

from .market_rules import round_to_lot


def position_size(
    equity: float,
    entry: float,
    stop: float,
    params: dict[str, Any],
    market: dict[str, Any],
) -> int:
    risk_per_share = entry - stop
    if equity <= 0 or entry <= 0 or risk_per_share <= 0:
        return 0
    risk_budget = equity * float(params["risk_per_trade"])
    risk_limited_shares = int(risk_budget // risk_per_share)
    max_shares = risk_limited_shares
    if market["cash_only"]:
        max_shares = min(max_shares, int(equity // entry))
    return round_to_lot(max_shares, market)


def monthly_halt(month_open_equity: float, equity: float, params: dict[str, Any]) -> bool:
    if month_open_equity <= 0:
        return False
    return equity < month_open_equity * (1 - float(params["monthly_drawdown_limit"]))


def protected_stop(entry: float, best_price: float, params: dict[str, Any]) -> float:
    if best_price <= entry:
        return entry
    return entry + float(params["profit_protect_ratio"]) * (best_price - entry)


def month_open_equity(equity: pd.Series) -> pd.Series:
    months = equity.index.to_period("M")
    return equity.groupby(months).transform("first")


def t_plus_one_allows(buy_date: date, sell_date: date, market: dict[str, Any]) -> bool:
    return not bool(market["t_plus_1"]) or sell_date > buy_date
