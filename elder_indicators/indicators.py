import numpy as np
import pandas as pd


def ema(df: pd.DataFrame, *, period: int, column: str = "close") -> pd.Series:
    return df[column].ewm(span=period, adjust=False, min_periods=period).mean().rename("ema")


def macd(
    df: pd.DataFrame, *, fast: int, slow: int, signal: int, column: str = "close"
) -> pd.DataFrame:
    fast_ema = df[column].ewm(span=fast, adjust=False, min_periods=fast).mean()
    slow_ema = df[column].ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame(
        {"macd": macd_line, "signal": signal_line, "histogram": macd_line - signal_line},
        index=df.index,
    )


def force_index(df: pd.DataFrame, *, period: int) -> pd.Series:
    raw_force = df["close"].diff() * df["volume"]
    result = raw_force.ewm(span=period, adjust=False, min_periods=period).mean()
    return result.where(df["volume"].notna()).rename("force_index")


def elder_ray(df: pd.DataFrame, *, period: int) -> pd.DataFrame:
    average = ema(df, period=period)
    return pd.DataFrame(
        {"bull_power": df["high"] - average, "bear_power": df["low"] - average},
        index=df.index,
    )


def stochastic(df: pd.DataFrame, *, k_period: int, d_period: int) -> pd.DataFrame:
    lowest = df["low"].rolling(k_period, min_periods=k_period).min()
    highest = df["high"].rolling(k_period, min_periods=k_period).max()
    spread = highest - lowest
    k_line = ((df["close"] - lowest) * 100 / spread).where(spread.ne(0))
    d_line = k_line.rolling(d_period, min_periods=d_period).mean()
    return pd.DataFrame({"stoch_k": k_line, "stoch_d": d_line}, index=df.index)


def rsi(df: pd.DataFrame, *, period: int, column: str = "close") -> pd.Series:
    change = df[column].diff()
    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    average_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    relative_strength = average_gain / average_loss
    result = 100 - 100 / (1 + relative_strength)
    result = result.mask(average_loss.eq(0) & average_gain.gt(0), 100)
    result = result.mask(average_gain.eq(0) & average_loss.gt(0), 0)
    result = result.mask(average_gain.eq(0) & average_loss.eq(0), 50)
    return result.rename("rsi")


def volume(df: pd.DataFrame) -> pd.Series:
    return df["volume"].rename("volume")


def calculate_indicators(df: pd.DataFrame, params: dict[str, object]) -> pd.DataFrame:
    result = pd.DataFrame(index=df.index)
    result["ema"] = ema(df, period=int(params["ema_period"]))
    result = result.join(
        macd(
            df,
            fast=int(params["macd_fast"]),
            slow=int(params["macd_slow"]),
            signal=int(params["macd_signal"]),
        )
    )
    result["force_index"] = force_index(df, period=int(params["fi_ema"]))
    result = result.join(elder_ray(df, period=int(params["ema_period"])))
    result = result.join(
        stochastic(df, k_period=int(params["stoch_k"]), d_period=int(params["stoch_d"]))
    )
    result["rsi"] = rsi(df, period=int(params["rsi_period"]))
    result["volume"] = volume(df)
    return result.replace([np.inf, -np.inf], np.nan)
