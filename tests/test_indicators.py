from __future__ import annotations

import unittest

import pandas as pd

from market_monitor.indicators import (
    calculate_drawdown,
    commodity_channel_index,
    daily_to_weekly,
    wilder_rsi,
)


class IndicatorTests(unittest.TestCase):
    def test_wilder_rsi_handles_rising_and_flat_prices(self) -> None:
        index = pd.date_range("2025-01-01", periods=20, freq="D", tz="UTC")
        rising = pd.Series(range(100, 120), index=index, dtype=float)
        flat = pd.Series([100.0] * 20, index=index)

        self.assertEqual(wilder_rsi(rising, 14).iloc[-1], 100.0)
        self.assertEqual(wilder_rsi(flat, 14).iloc[-1], 50.0)

    def test_wilder_rsi_matches_reference_example(self) -> None:
        close = pd.Series(
            [
                44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
                45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28,
            ]
        )

        self.assertAlmostEqual(wilder_rsi(close, 14).iloc[-1], 70.4641, places=4)

    def test_cci_is_zero_for_constant_typical_price(self) -> None:
        series = pd.Series([100.0] * 25)
        cci = commodity_channel_index(series, series, series, period=20)
        self.assertEqual(cci.iloc[-1], 0.0)

    def test_partial_week_is_excluded(self) -> None:
        index = pd.date_range("2025-01-06", "2025-01-15", freq="B", tz="UTC")
        values = pd.Series(range(len(index)), index=index, dtype=float) + 100
        daily = pd.DataFrame(
            {"Open": values, "High": values + 1, "Low": values - 1, "Close": values}
        )

        weekly = daily_to_weekly(daily, exclude_incomplete_week=True)

        self.assertEqual(len(weekly), 1)
        self.assertEqual(weekly.index[-1], pd.Timestamp("2025-01-10", tz="UTC"))

    def test_drawdown_uses_peak_and_optional_latest_value(self) -> None:
        close = pd.Series(
            [100.0, 120.0, 108.0],
            index=pd.date_range("2025-01-01", periods=3, freq="D", tz="UTC"),
        )

        result = calculate_drawdown(close, latest_value=90.0)

        self.assertEqual(result.peak, 120.0)
        self.assertEqual(result.latest, 90.0)
        self.assertAlmostEqual(result.percent, -25.0)


if __name__ == "__main__":
    unittest.main()
