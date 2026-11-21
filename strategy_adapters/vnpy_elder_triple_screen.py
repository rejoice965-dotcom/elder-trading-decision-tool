from pathlib import Path

import pandas as pd
from vnpy_ctastrategy import BarData, CtaTemplate

from elder_indicators.config import load_config
from elder_indicators.signals import build_triple_screen_signals
from market_data.provider import load_cached


CONFIG = load_config()


class VnpyElderTripleScreen(CtaTemplate):
    """VN.py adapter; all indicator and signal calculations stay in elder_indicators."""

    author = "Elder Triple Screen"
    parameters = ["cache_directory"]
    variables = []
    cache_directory = CONFIG["market"]["cache"]["directory"]

    def on_init(self) -> None:
        self.write_log("仅供研究与回测，不构成投资建议")
        symbol = self._product_symbol(self.vt_symbol)
        cache_path = Path(__file__).resolve().parents[1] / self.cache_directory
        try:
            bundle = load_cached(symbol, cache_path)
        except FileNotFoundError:
            self.write_log(f"未找到 {symbol} 本地行情缓存，请先运行 market_data.provider")
            return
        weekly, daily, intraday = bundle.signal_frames(CONFIG["market"])
        self._signals = self.signals_from_frames(weekly, daily, intraday, symbol=symbol)
        self.write_log(f"已从本地缓存计算 {len(self._signals)} 条信号")

    def on_bar(self, bar: BarData) -> None:
        self.update_signal_chart(bar, getattr(self, "_signals", pd.DataFrame()))
        self.put_event()

    def on_stop(self) -> None:
        return

    def signals_from_frames(
        self,
        weekly_qfq: pd.DataFrame,
        daily_tracks: pd.DataFrame,
        intraday_tracks: pd.DataFrame,
        *,
        symbol: str | None = None,
    ) -> pd.DataFrame:
        symbol = self._product_symbol(symbol or self.vt_symbol)
        result = build_triple_screen_signals(
            weekly_qfq,
            daily_tracks,
            intraday_tracks,
            symbol=symbol,
            params=CONFIG["params"],
            market=CONFIG["market"],
        )
        return result

    @staticmethod
    def _product_symbol(vt_symbol: str) -> str:
        if vt_symbol.endswith(".SSE"):
            return vt_symbol[:-4] + ".SH"
        if vt_symbol.endswith(".SZSE"):
            return vt_symbol[:-5] + ".SZ"
        return vt_symbol

    def update_signal_chart(self, bar: BarData, signals: pd.DataFrame) -> None:
        """Draw an active signal level on the candle chart; trade fills are native VN.py markers."""
        if signals.empty:
            return
        matches = signals.loc[pd.to_datetime(signals["timestamp"]).eq(pd.Timestamp(bar.datetime))]
        if matches.empty:
            return
        side = str(matches.iloc[-1]["side"])
        color = "red" if side == "BUY" else "green"
        self.add_horizontal_line_to_candle_chart(
            f"{side} signal {matches.iloc[-1]['rule_id']}",
            float(matches.iloc[-1]["price"]),
            color,
        )


def evaluate_signal_frames(
    weekly_qfq: pd.DataFrame,
    daily_tracks: pd.DataFrame,
    intraday_tracks: pd.DataFrame,
    symbol: str,
    config_path: Path | None = None,
) -> pd.DataFrame:
    config = load_config(config_path) if config_path else CONFIG
    return build_triple_screen_signals(
        weekly_qfq,
        daily_tracks,
        intraday_tracks,
        symbol=symbol,
        params=config["params"],
        market=config["market"],
    )
