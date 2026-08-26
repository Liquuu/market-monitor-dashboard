"""Yahoo Finance adapter implemented with yfinance."""

from __future__ import annotations

import math

import pandas as pd
import yfinance as yf

from ..models import Quote


class DataProviderError(RuntimeError):
    """Raised when a provider response cannot be used."""


class YahooFinanceProvider:
    def __init__(self, timeout_seconds: int = 30, retries: int = 3) -> None:
        self.timeout_seconds = timeout_seconds
        self.retries = retries

    def _history(self, symbol: str, *, period: str, interval: str) -> pd.DataFrame:
        last_error: Exception | None = None
        for _attempt in range(self.retries):
            try:
                frame = yf.Ticker(symbol).history(
                    period=period,
                    interval=interval,
                    auto_adjust=False,
                    actions=False,
                    repair=False,
                    timeout=self.timeout_seconds,
                )
                if isinstance(frame, pd.DataFrame) and not frame.empty:
                    return frame
                last_error = DataProviderError(
                    f"Yahoo Finance returned no {interval} data for {symbol}"
                )
            except Exception as error:  # yfinance exposes several transport exceptions
                last_error = error
        raise DataProviderError(
            f"Yahoo Finance request failed for {symbol} after {self.retries} attempts: "
            f"{last_error}"
        ) from last_error

    def fetch_latest(self, symbol: str) -> Quote:
        try:
            frame = self._history(symbol, period="5d", interval="1h")
        except DataProviderError:
            frame = self._history(symbol, period="5d", interval="1d")

        if "Close" not in frame:
            raise DataProviderError(f"Yahoo Finance response has no Close column for {symbol}")
        close = pd.to_numeric(frame["Close"], errors="coerce").dropna()
        if close.empty:
            raise DataProviderError(f"Yahoo Finance response has no valid close for {symbol}")
        value = float(close.iloc[-1])
        if not math.isfinite(value):
            raise DataProviderError(f"Yahoo Finance returned a non-finite close for {symbol}")
        observed_at = pd.Timestamp(close.index[-1])
        if observed_at.tzinfo is None:
            observed_at = observed_at.tz_localize("UTC")
        else:
            observed_at = observed_at.tz_convert("UTC")
        return Quote(value=value, observed_at=observed_at.to_pydatetime())

    def fetch_daily_history(self, symbol: str, period: str = "max") -> pd.DataFrame:
        frame = self._history(symbol, period=period, interval="1d")
        required = ["Open", "High", "Low", "Close"]
        missing = [column for column in required if column not in frame]
        if missing:
            raise DataProviderError(
                f"Yahoo Finance response for {symbol} is missing: {', '.join(missing)}"
            )
        result = frame.loc[:, required].apply(pd.to_numeric, errors="coerce")
        result = result.dropna(subset=required)
        result.index = pd.to_datetime(result.index, utc=True)
        result = result[~result.index.duplicated(keep="last")].sort_index()
        if result.empty:
            raise DataProviderError(f"Yahoo Finance returned no valid daily rows for {symbol}")
        return result
