import numpy as np
import pandas as pd

from elder_indicators.indicators import (
    elder_ray,
    ema,
    force_index,
    macd,
    rsi,
    stochastic,
    volume,
)


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [10, 11, 10, 12, 12],
            "high": [11, 12, 11, 13, 13],
            "low": [9, 10, 9, 11, 11],
            "close": [10, 11, 10, 12, 12],
            "volume": [1, 2, 3, 4, 5],
        },
        index=pd.date_range("2026-01-05", periods=5, freq="D"),
    )


def test_ema_warmup_and_hand_calculated_values() -> None:
    result = ema(sample_frame(), period=3)
    assert result.iloc[:2].isna().all()
    np.testing.assert_allclose(result.iloc[2:].to_numpy(), [10.25, 11.125, 11.5625])


def test_force_index_and_missing_volume_boundary() -> None:
    frame = sample_frame()
    result = force_index(frame, period=2)
    np.testing.assert_allclose(
        result.iloc[1:].to_numpy(), [np.nan, -1.3333333333, 4.8888888889, 1.6296296296], equal_nan=True
    )

    frame.loc[frame.index[2], "volume"] = np.nan
    missing_result = force_index(frame, period=2)
    assert pd.isna(missing_result.iloc[2])
    assert pd.isna(volume(frame).iloc[2])


def test_macd_line_signal_and_histogram_hand_calculated_values() -> None:
    result = macd(sample_frame(), fast=2, slow=3, signal=2)
    assert result.iloc[:2].isna().all().all()
    np.testing.assert_allclose(
        result.loc[result.index[3], ["macd", "signal", "histogram"]].to_numpy(),
        [0.2824074074, 0.1790123457, 0.1033950617],
    )
    np.testing.assert_allclose(
        result.loc[result.index[4], ["macd", "signal", "histogram"]].to_numpy(),
        [0.2399691358, 0.2196502058, 0.02031893],
        atol=1e-7,
    )


def test_stochastic_and_zero_range() -> None:
    frame = sample_frame()
    result = stochastic(frame, k_period=3, d_period=2)
    np.testing.assert_allclose(result["stoch_k"].iloc[2:].to_numpy(), [33.3333333333, 75.0, 75.0])
    np.testing.assert_allclose(result["stoch_d"].iloc[3:].to_numpy(), [54.1666666667, 75.0])

    constant = frame.assign(high=10.0, low=10.0, close=10.0)
    assert stochastic(constant, k_period=3, d_period=2).isna().all().all()


def test_rsi_flat_gain_loss_and_constant_price() -> None:
    result = rsi(sample_frame(), period=3)
    assert pd.isna(result.iloc[2])
    np.testing.assert_allclose(result.iloc[3:].to_numpy(), [83.3333333333, 83.3333333333])

    constant = sample_frame().assign(close=10.0)
    np.testing.assert_allclose(rsi(constant, period=3).iloc[3:].to_numpy(), [50.0, 50.0])


def test_elder_ray_respects_ema_warmup() -> None:
    result = elder_ray(sample_frame(), period=3)
    assert result.iloc[:2].isna().all().all()
    np.testing.assert_allclose(
        result.iloc[2:].to_numpy(),
        [[0.75, -1.25], [1.875, -0.125], [1.4375, -0.5625]],
    )


def test_volume_preserves_observed_values() -> None:
    np.testing.assert_array_equal(volume(sample_frame()).to_numpy(), [1, 2, 3, 4, 5])
