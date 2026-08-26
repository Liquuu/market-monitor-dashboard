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

    def build(self) -> dict[str, object]:
        quotes = {
            key: self.provider.fetch_latest(instrument.symbol)
            for key, instrument in self.config.instruments.items()
        }

        history_by_key: dict[str, pd.DataFrame] = {}
        for key in {self.config.weekly.instrument, self.config.drawdown.instrument}:
            history_by_key[key] = self.provider.fetch_daily_history(
                self.config.instruments[key].symbol, period="max"
            )

        weekly_config = self.config.weekly
        weekly = compute_weekly_indicators(
            history_by_key[weekly_config.instrument],
            rsi_period=weekly_config.rsi_period,
            cci_period=weekly_config.cci_period,
            cci_constant=weekly_config.cci_constant,
            exclude_incomplete_week=weekly_config.exclude_incomplete_week,
        ).dropna(subset=["RSI", "CCI"])
        if weekly.empty:
            raise ValueError("Not enough weekly history to calculate RSI and CCI")
        weekly_latest = weekly.iloc[-1]

        drawdown_config = self.config.drawdown
        drawdown_instrument = self.config.instruments[drawdown_config.instrument]
        drawdown_quote = quotes[drawdown_config.instrument]
        drawdown = calculate_drawdown(
            history_by_key[drawdown_config.instrument][drawdown_config.price_field],
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
            "schema_version": 1,
            "mode": "live",
            "generated_at": _iso_utc(self.now_factory()),
            "status": {
                "state": "ready",
                "message": "市場データを正常に取得しました。",
            },
            "metrics": metrics,
            "weekly": {
                "as_of": _iso_utc(weekly.index[-1]),
                "cci": round(float(weekly_latest["CCI"]), 2),
                "rsi": round(float(weekly_latest["RSI"]), 2),
            },
        }
