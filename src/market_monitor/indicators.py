"""Indicator and market-series calculations."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .models import DrawdownResult


REQUIRED_OHLC_COLUMNS = ("Open", "High", "Low", "Close")


def _numeric_series(values: pd.Series, name: str) -> pd.Series:
    series = pd.to_numeric(values, errors="coerce").astype(float)
    if series.dropna().empty:
        raise ValueError(f"{name} contains no numeric values")
    return series


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI using Wilder's original smoothed-average recurrence."""

    if period <= 0:
        raise ValueError("period must be positive")

    values = _numeric_series(close, "close")
    result = pd.Series(np.nan, index=values.index, dtype=float, name="RSI")
    if len(values) <= period:
        return result

    delta = values.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.iloc[1 : period + 1].mean()
    average_loss = losses.iloc[1 : period + 1].mean()

    def score(gain: float, loss: float) -> float:
        if math.isclose(gain, 0.0) and math.isclose(loss, 0.0):
            return 50.0
        if math.isclose(loss, 0.0):
            return 100.0
        if math.isclose(gain, 0.0):
            return 0.0
        relative_strength = gain / loss
        return 100.0 - (100.0 / (1.0 + relative_strength))

    result.iloc[period] = score(average_gain, average_loss)
    for position in range(period + 1, len(values)):
        current_gain = gains.iloc[position]
        current_loss = losses.iloc[position]
        if pd.isna(current_gain) or pd.isna(current_loss):
            average_gain = math.nan
            average_loss = math.nan
            continue
        if math.isnan(average_gain) or math.isnan(average_loss):
            window_gain = gains.iloc[position - period + 1 : position + 1]
            window_loss = losses.iloc[position - period + 1 : position + 1]
            if window_gain.isna().any() or window_loss.isna().any():
                continue
            average_gain = window_gain.mean()
            average_loss = window_loss.mean()
        else:
            average_gain = ((average_gain * (period - 1)) + current_gain) / period
            average_loss = ((average_loss * (period - 1)) + current_loss) / period
        result.iloc[position] = score(average_gain, average_loss)

    return result


def commodity_channel_index(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 20,
    constant: float = 0.015,
) -> pd.Series:
    """Calculate CCI from typical price and rolling mean absolute deviation."""

    if period <= 0:
        raise ValueError("period must be positive")
    if constant <= 0:
        raise ValueError("constant must be positive")

    typical_price = (
        _numeric_series(high, "high")
        + _numeric_series(low, "low")
        + _numeric_series(close, "close")
    ) / 3.0
    moving_average = typical_price.rolling(period, min_periods=period).mean()
    mean_deviation = typical_price.rolling(period, min_periods=period).apply(
        lambda window: np.mean(np.abs(window - np.mean(window))), raw=True
    )
    denominator = constant * mean_deviation
    result = (typical_price - moving_average) / denominator
    result = result.mask(denominator == 0, 0.0)
    result.name = "CCI"
    return result


def daily_to_weekly(
    daily: pd.DataFrame, *, exclude_incomplete_week: bool = True
) -> pd.DataFrame:
    """Aggregate daily OHLC bars into Friday-labelled weekly bars."""

    missing = [column for column in REQUIRED_OHLC_COLUMNS if column not in daily.columns]
    if missing:
        raise ValueError(f"daily data is missing columns: {', '.join(missing)}")
    if daily.empty:
        raise ValueError("daily data is empty")

    frame = daily.loc[:, REQUIRED_OHLC_COLUMNS].copy()
    frame.index = pd.to_datetime(frame.index, utc=True)
    frame = frame.sort_index()
    latest_source_date = frame.index[-1].date()
    weekly = frame.resample("W-FRI").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    )
    weekly = weekly.dropna(subset=list(REQUIRED_OHLC_COLUMNS))
    if exclude_incomplete_week and not weekly.empty:
        weekly = weekly[weekly.index.date <= latest_source_date]
    return weekly


def compute_weekly_indicators(
    daily: pd.DataFrame,
    *,
    rsi_period: int,
    cci_period: int,
    cci_constant: float,
    exclude_incomplete_week: bool,
) -> pd.DataFrame:
    weekly = daily_to_weekly(
        daily, exclude_incomplete_week=exclude_incomplete_week
    )
    weekly["RSI"] = wilder_rsi(weekly["Close"], rsi_period)
    weekly["CCI"] = commodity_channel_index(
        weekly["High"],
        weekly["Low"],
        weekly["Close"],
        cci_period,
        cci_constant,
    )
    return weekly


def calculate_drawdown(
    close: pd.Series,
    *,
    latest_value: float | None = None,
    lookback_days: int | None = None,
) -> DrawdownResult:
    """Return closing-price drawdown from the peak (zero or negative percent)."""

    values = _numeric_series(close, "close").dropna().sort_index()
    if lookback_days is not None:
        if lookback_days <= 0:
            raise ValueError("lookback_days must be positive")
        cutoff = pd.Timestamp(values.index[-1]) - pd.Timedelta(days=lookback_days)
        values = values[values.index >= cutoff]
    if values.empty:
        raise ValueError("close contains no values in the requested lookback")

    latest = float(values.iloc[-1] if latest_value is None else latest_value)
    if not math.isfinite(latest) or latest <= 0:
        raise ValueError("latest value must be a positive finite number")
    peak = max(float(values.max()), latest)
    percent = ((latest / peak) - 1.0) * 100.0
    return DrawdownResult(latest=latest, peak=peak, percent=percent)
