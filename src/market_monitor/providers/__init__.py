"""Market-data provider interfaces."""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from ..models import Quote


class MarketDataProvider(Protocol):
    def fetch_latest(self, symbol: str) -> Quote: ...

    def fetch_daily_history(self, symbol: str, period: str = "max") -> pd.DataFrame: ...
