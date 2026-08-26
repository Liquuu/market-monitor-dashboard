from __future__ import annotations

from datetime import datetime, timezone
import unittest

import pandas as pd

from market_monitor.config import (
    DashboardConfig,
    DrawdownConfig,
    InstrumentConfig,
    StorageConfig,
    WeeklyIndicatorConfig,
)
from market_monitor.models import Quote
from market_monitor.service import SnapshotService


class FakeProvider:
    def __init__(self) -> None:
        index = pd.date_range("2024-01-01", periods=400, freq="B", tz="UTC")
        close = pd.Series([100.0 + position * 0.25 for position in range(len(index))], index=index)
        self.history = pd.DataFrame(
            {"Open": close - 0.1, "High": close + 1, "Low": close - 1, "Close": close}
        )
        self.latest = {
            "^NDX": 195.0,
            "^SKEW": 145.25,
            "^VIX": 18.5,
            "BZ=F": 72.3,
            "^TNX": 4.125,
        }

    def fetch_latest(self, symbol: str) -> Quote:
        return Quote(self.latest[symbol], datetime(2025, 7, 11, 20, tzinfo=timezone.utc))

    def fetch_daily_history(self, symbol: str, period: str = "max") -> pd.DataFrame:
        self.assert_period = period
        return self.history.copy()


class SnapshotServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        symbols = {
            "nasdaq100": "^NDX",
            "skew": "^SKEW",
            "vix": "^VIX",
            "brent": "BZ=F",
            "us10y": "^TNX",
        }
        instruments = {
            key: InstrumentConfig(
                key=key,
                label=key,
                provider="yahoo",
                symbol=symbol,
                unit="index",
                decimals=3 if key == "us10y" else 2,
                source_url=f"https://example.com/{key}",
            )
            for key, symbol in symbols.items()
        }
        self.config = DashboardConfig(
            timezone="Asia/Tokyo",
            yahoo_timeout_seconds=30,
            yahoo_retries=3,
            instruments=instruments,
            weekly=WeeklyIndicatorConfig("nasdaq100", True, 14, 20, 0.015),
            drawdown=DrawdownConfig("nasdaq100", "Close", None),
            storage=StorageConfig(5, 10, True),
        )

    def test_snapshot_matches_dashboard_contract(self) -> None:
        service = SnapshotService(
            self.config,
            FakeProvider(),
            now_factory=lambda: datetime(2025, 7, 12, tzinfo=timezone.utc),
        )

        payload = service.build()

        self.assertEqual(payload["mode"], "live")
        self.assertEqual(payload["status"]["state"], "ready")
        self.assertEqual(payload["metrics"]["skew"]["value"], 145.25)
        self.assertIsNone(payload["metrics"]["skew"]["delta"])
        self.assertLessEqual(payload["metrics"]["nasdaq100_drawdown"]["value"], 0)
        self.assertIsInstance(payload["weekly"]["rsi"], float)
        self.assertIsInstance(payload["weekly"]["cci"], float)


if __name__ == "__main__":
    unittest.main()
