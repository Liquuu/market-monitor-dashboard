from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from market_monitor.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def test_repository_config_loads(self) -> None:
        config = load_config(Path("config/config.yaml"))

        self.assertEqual(config.instruments["nasdaq100"].symbol, "^NDX")
        self.assertEqual(config.yahoo_retries, 3)
        self.assertEqual(config.weekly.rsi_period, 14)
        self.assertEqual(config.drawdown.price_field, "Close")

    def test_unknown_indicator_instrument_is_rejected(self) -> None:
        content = """
project: {timezone: Asia/Tokyo}
providers: {yahoo: {request_timeout_seconds: 30}}
instruments:
  known: {label: Known, provider: yahoo, symbol: TEST, unit: index, decimals: 2, source_url: https://example.com}
indicators:
  weekly:
    instrument: missing
    rsi: {period: 14}
    cci: {period: 20, constant: 0.015}
  drawdown: {instrument: known, price_field: close, lookback_days: null}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
