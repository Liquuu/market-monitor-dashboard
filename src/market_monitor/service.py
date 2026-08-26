"""Build the dashboard's latest market snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

import pandas as pd

from .config import DashboardConfig, InstrumentConfig
from .indicators import calculate_drawdown, compute_weekly_indicators
from .models import Quote
from .providers import MarketDataProvider


def _iso_utc(value: datetime | pd.Timestamp) -> str:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return timestamp.isoformat().replace("+00:00", "Z")


class SnapshotService:
    def __init__(
        self,
        config: DashboardConfig,
        provider: MarketDataProvider,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self.provider = provider
        self.now_factory = now_factory or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _metric(instrument: InstrumentConfig, quote: Quote) -> dict[str, object]:
        return {
            "label": instrument.label,
            "value": round(quote.value, instrument.decimals),
            "delta": None,
            "unit": instrument.unit,
            "decimals": instrument.decimals,
            "observed_at": _iso_utc(quote.observed_at),
            "source_url": instrument.source_url,
        }

    def build_intraday(self) -> dict[str, object]:
        """Fetch the twice-daily values and calculate NASDAQ 100 drawdown."""

        quotes = {
            key: self.provider.fetch_latest(instrument.symbol)
            for key, instrument in self.config.instruments.items()
        }
        drawdown_config = self.config.drawdown
        drawdown_instrument = self.config.instruments[drawdown_config.instrument]
        drawdown_quote = quotes[drawdown_config.instrument]
        daily = self.provider.fetch_daily_history(drawdown_instrument.symbol, period="max")
        drawdown = calculate_drawdown(
            daily[drawdown_config.price_field],
            latest_value=drawdown_quote.value,
            lookback_days=drawdown_config.lookback_days,
        )

        metrics = {
            key: self._metric(self.config.instruments[key], quotes[key])
            for key in ("skew", "vix", "brent", "us10y")
        }
        metrics["nasdaq100_drawdown"] = {
            "label": "NASDAQ 100 Drawdown",
            "value": round(drawdown.percent, 2),
            "delta": None,
            "unit": "%",
            "decimals": 2,
            "observed_at": _iso_utc(drawdown_quote.observed_at),
            "source_url": drawdown_instrument.source_url,
        }

        return {
            "generated_at": _iso_utc(self.now_factory()),
            "metrics": metrics,
        }

    def build_weekly(self) -> dict[str, object]:
        """Fetch daily history and calculate the latest confirmed weekly values."""

        weekly_config = self.config.weekly
        instrument = self.config.instruments[weekly_config.instrument]
        daily = self.provider.fetch_daily_history(instrument.symbol, period="max")
        weekly = compute_weekly_indicators(
            daily,
            rsi_period=weekly_config.rsi_period,
            cci_period=weekly_config.cci_period,
            cci_constant=weekly_config.cci_constant,
            exclude_incomplete_week=weekly_config.exclude_incomplete_week,
        ).dropna(subset=["RSI", "CCI"])
        if weekly.empty:
            raise ValueError("Not enough weekly history to calculate RSI and CCI")
        weekly_latest = weekly.iloc[-1]
        history = [
            {
                "as_of": _iso_utc(index),
                "close": round(float(row["Close"]), 2),
                "cci": round(float(row["CCI"]), 2),
                "rsi": round(float(row["RSI"]), 2),
            }
            for index, row in weekly.iterrows()
        ]
        return {
            "generated_at": _iso_utc(self.now_factory()),
            "weekly": {
                "as_of": _iso_utc(weekly.index[-1]),
                "cci": round(float(weekly_latest["CCI"]), 2),
                "rsi": round(float(weekly_latest["RSI"]), 2),
            },
            "weekly_history": history,
        }

    def build(self) -> dict[str, object]:
        """Build a complete snapshot (kept for local use and compatibility)."""

        intraday = self.build_intraday()
        weekly = self.build_weekly()
        return {
            "schema_version": 1,
            "mode": "live",
            "generated_at": intraday["generated_at"],
            "status": {
                "state": "ready",
                "message": "市場データを正常に取得しました。",
            },
            "metrics": intraday["metrics"],
            "weekly": weekly["weekly"],
        }
