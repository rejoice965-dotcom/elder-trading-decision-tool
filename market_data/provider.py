import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from elder_indicators.config import load_config
from .bars import (
    annotate_intraday_status,
    apply_adjustment_factor,
    aggregate_weekly_from_daily,
    normalize_bars,
)


@dataclass
class MarketDataBundle:
    daily_qfq: pd.DataFrame
    daily_raw: pd.DataFrame
    intraday_qfq: pd.DataFrame
    intraday_raw: pd.DataFrame
    metadata: dict[str, Any]

    def signal_frames(
        self, market: dict[str, Any]
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        daily_tracks = self.daily_qfq.copy()
        for column in ("open", "high", "low", "close", "volume"):
            daily_tracks[f"{column}_raw"] = self.daily_raw[column].reindex(daily_tracks.index)
        weekly_qfq = aggregate_weekly_from_daily(self.daily_qfq, market)
        return weekly_qfq, daily_tracks, self.intraday_qfq


def fetch_history(
    symbol: str,
    start_date: str,
    end_date: str,
    *,
    config: dict[str, Any] | None = None,
    cache_dir: Path | None = None,
    provider_override: str | None = None,
) -> MarketDataBundle:
    config = config or load_config()
    market = config["market"]
    provider = provider_override or market["data_source"]
    code = symbol.split(".", 1)[0]
    start_compact = pd.Timestamp(start_date).strftime("%Y%m%d")
    end_compact = pd.Timestamp(end_date).strftime("%Y%m%d")

    if provider in {"akshare", "akshare_sina"}:
        sina_only = provider == "akshare_sina"
        daily_qfq = _fetch_akshare_daily(code, start_compact, end_compact, "qfq", sina_only=sina_only)
        daily_raw = _fetch_akshare_daily(code, start_compact, end_compact, "", sina_only=sina_only)
        intraday_raw = _fetch_akshare_intraday(code, start_date, end_date, sina_only=sina_only)
    elif provider == "baostock":
        daily_qfq, daily_raw, intraday_raw = _fetch_baostock(code, start_date, end_date)
    else:
        raise ValueError(f"Unsupported live provider: {provider}")

    daily_qfq = _annotate_daily_closed(_at_daily_close(daily_qfq, market), market)
    daily_raw = _annotate_daily_closed(_at_daily_close(daily_raw, market), market)
    intraday_raw = annotate_intraday_status(intraday_raw, market)
    intraday_qfq = apply_adjustment_factor(intraday_raw, daily_raw, daily_qfq)
    fetched_at = datetime.now().astimezone().isoformat(timespec="seconds")
    metadata = {
        "symbol": symbol,
        "provider": provider,
        "requested_start_date": start_date,
        "requested_end_date": end_date,
        "actual_daily_start": _date_text(daily_qfq.index.min()),
        "actual_daily_end": _date_text(daily_qfq.index.max()),
        "actual_intraday_start": _date_text(intraday_raw.index.min()),
        "actual_intraday_end": _date_text(intraday_raw.index.max()),
        "fetched_at": fetched_at,
        "indicator_adjustment": market["adjustment_tracks"]["indicators"],
        "execution_adjustment": market["adjustment_tracks"]["execution"],
        "limit_validation_adjustment": market["adjustment_tracks"]["limit_validation"],
    }
    bundle = MarketDataBundle(daily_qfq, daily_raw, intraday_qfq, intraday_raw, metadata)
    default_cache = Path(__file__).resolve().parents[1] / market["cache"]["directory"]
    _cache_bundle(bundle, symbol, cache_dir or default_cache)
    return bundle


def _date_text(value: pd.Timestamp) -> str | None:
    return None if pd.isna(value) else pd.Timestamp(value).isoformat()


def load_cached(symbol: str, cache_dir: Path) -> MarketDataBundle:
    code = symbol.replace(".", "_")
    metadata = json.loads((cache_dir / f"{code}_metadata.json").read_text(encoding="utf-8"))
    market = load_config()["market"]
    return MarketDataBundle(
        _at_daily_close(_read_frame(cache_dir / f"{code}_daily_qfq.csv"), market),
        _at_daily_close(_read_frame(cache_dir / f"{code}_daily_raw.csv"), market),
        _read_frame(cache_dir / f"{code}_60m_qfq.csv"),
        _read_frame(cache_dir / f"{code}_60m_raw.csv"),
        metadata,
    )


def _fetch_akshare_daily(
    code: str, start: str, end: str, adjust: str, *, sina_only: bool = False
) -> pd.DataFrame:
    import akshare as ak

    if sina_only:
        frame = ak.stock_zh_a_hist_sina(
            symbol=_sina_symbol(code),
            period="daily",
            start_date=start,
            end_date=end,
            adjust=adjust,
        )
    else:
        try:
            frame = ak.stock_zh_a_hist_em(
                symbol=code,
                period="daily",
                start_date=start,
                end_date=end,
                adjust=adjust,
            )
        except Exception as eastmoney_error:
            try:
                frame = ak.stock_zh_a_hist_sina(
                    symbol=_sina_symbol(code),
                    period="daily",
                    start_date=start,
                    end_date=end,
                    adjust=adjust,
                )
            except Exception as sina_error:
                raise RuntimeError(
                    f"AkShare daily sources failed. EastMoney: {eastmoney_error}; Sina: {sina_error}"
                ) from sina_error
        if frame.empty:
            frame = ak.stock_zh_a_hist_sina(
                symbol=_sina_symbol(code),
                period="daily",
                start_date=start,
                end_date=end,
                adjust=adjust,
            )
    return normalize_bars(frame)


def _fetch_akshare_intraday(
    code: str, start: str, end: str, *, sina_only: bool = False
) -> pd.DataFrame:
    import akshare as ak

    if sina_only:
        frame = ak.stock_zh_a_hist_min_sina(
            symbol=_sina_symbol(code), period="60", adjust=""
        )
    else:
        try:
            frame = ak.stock_zh_a_hist_min_em(
                symbol=code,
                start_date=f"{start} 00:00:00",
                end_date=f"{end} 23:59:59",
                period="60",
                adjust="",
            )
        except Exception as eastmoney_error:
            try:
                frame = ak.stock_zh_a_hist_min_sina(
                    symbol=_sina_symbol(code), period="60", adjust=""
                )
            except Exception as sina_error:
                raise RuntimeError(
                    f"AkShare intraday sources failed. EastMoney: {eastmoney_error}; Sina: {sina_error}"
                ) from sina_error
        if frame.empty:
            frame = ak.stock_zh_a_hist_min_sina(
                symbol=_sina_symbol(code), period="60", adjust=""
            )
    normalized = normalize_bars(frame)
    start_bound = pd.Timestamp(start)
    end_bound = pd.Timestamp(end) + pd.Timedelta("1D") - pd.Timedelta("1ns")
    return normalized.loc[start_bound:end_bound]


def _sina_symbol(code: str) -> str:
    market = "sh" if code.startswith(("5", "6", "9")) else "sz"
    return market + code


def _annotate_daily_closed(frame: pd.DataFrame, market: dict[str, Any]) -> pd.DataFrame:
    result = frame.copy()
    now = pd.Timestamp.now()
    close_time = pd.Timestamp(market["trading_sessions"]["afternoon_close"]).time()
    result["is_closed"] = [
        stamp.date() < now.date() or (stamp.date() == now.date() and now.time() >= close_time)
        for stamp in result.index
    ]
    return result


def _at_daily_close(frame: pd.DataFrame, market: dict[str, Any]) -> pd.DataFrame:
    result = frame.copy()
    close_time = market["trading_sessions"]["afternoon_close"]
    result.index = pd.DatetimeIndex(result.index).normalize() + pd.to_timedelta(f"{close_time}:00")
    result.index.name = "timestamp"
    return result


def _fetch_baostock(code: str, start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    import baostock as bs

    exchange_code = "sh" if code.startswith(("5", "6", "9")) else "sz"
    response = bs.login()
    if response.error_code != "0":
        raise RuntimeError(response.error_msg)
    try:
        daily_qfq = _baostock_query(bs, f"{exchange_code}.{code}", start, end, "d", "2")
        daily_raw = _baostock_query(bs, f"{exchange_code}.{code}", start, end, "d", "3")
        intraday_raw = _baostock_query(bs, f"{exchange_code}.{code}", start, end, "60", "3")
    finally:
        bs.logout()
    return daily_qfq, daily_raw, intraday_raw


def _baostock_query(bs: Any, code: str, start: str, end: str, frequency: str, adjust: str) -> pd.DataFrame:
    fields = "date,code,open,high,low,close,volume,amount"
    if frequency != "d":
        fields = "date,time,code,open,high,low,close,volume,amount"
    response = bs.query_history_k_data_plus(
        code,
        fields,
        start_date=start,
        end_date=end,
        frequency=frequency,
        adjustflag=adjust,
    )
    rows = []
    while response.next():
        rows.append(response.get_row_data())
    if response.error_code != "0":
        raise RuntimeError(response.error_msg)
    frame = pd.DataFrame(rows, columns=response.fields)
    if "time" in frame:
        frame["timestamp"] = frame["time"].where(frame["time"].ne(""), frame["date"])
    else:
        frame["timestamp"] = frame["date"]
    frame = frame.drop(columns=[column for column in ("date", "time") if column in frame])
    return normalize_bars(frame)


def _cache_bundle(bundle: MarketDataBundle, symbol: str, cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    code = symbol.replace(".", "_")
    frames = {
        "daily_qfq": bundle.daily_qfq,
        "daily_raw": bundle.daily_raw,
        "60m_qfq": bundle.intraday_qfq,
        "60m_raw": bundle.intraday_raw,
    }
    for name, frame in frames.items():
        frame.to_csv(cache_dir / f"{code}_{name}.csv", index_label="timestamp")
    (cache_dir / f"{code}_metadata.json").write_text(
        json.dumps(bundle.metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _read_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp")
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and cache A-share OHLCV data")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--provider", choices=("akshare", "akshare_sina", "baostock"))
    args = parser.parse_args()
    result = fetch_history(
        args.symbol,
        args.start_date,
        args.end_date,
        cache_dir=args.cache_dir,
        provider_override=args.provider,
    )
    print(json.dumps({**result.metadata, "daily_qfq_rows": len(result.daily_qfq), "daily_raw_rows": len(result.daily_raw), "intraday_qfq_rows": len(result.intraday_qfq), "intraday_raw_rows": len(result.intraday_raw)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
