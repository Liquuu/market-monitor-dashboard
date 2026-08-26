from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from market_monitor.config import StorageConfig
from market_monitor.storage import DashboardStore, StorageError


def metric(value: float, observed_at: str, decimals: int = 2) -> dict[str, object]:
    return {
        "label": "Example",
        "value": value,
        "delta": None,
        "unit": "index",
        "decimals": decimals,
        "observed_at": observed_at,
        "source_url": "https://example.com",
    }


class DashboardStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.latest_path = root / "data" / "latest.json"
        self.history_dir = root / "data" / "history"
        self.store = DashboardStore(
            self.latest_path, self.history_dir, StorageConfig(5, 10, True)
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def snapshot(self, value: float, observed_at: str) -> dict[str, object]:
        return {
            "generated_at": observed_at,
            "metrics": {"vix": metric(value, observed_at)},
            "weekly": {"as_of": "2025-01-03T00:00:00Z", "cci": 25.0, "rsi": 55.0},
        }

    def test_first_update_writes_both_histories(self) -> None:
        result = self.store.update(self.snapshot(20.0, "2025-01-06T12:00:00Z"))

        self.assertTrue(result.intraday_appended)
        self.assertTrue(result.weekly_appended)
        self.assertEqual(result.payload["mode"], "live")
        self.assertIsNone(result.payload["metrics"]["vix"]["delta"])
        intraday = json.loads(
            (self.history_dir / "intraday.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(intraday["observations"]), 1)

    def test_second_update_calculates_delta_and_skips_same_week(self) -> None:
        self.store.update(self.snapshot(20.0, "2025-01-06T12:00:00Z"))
        result = self.store.update(self.snapshot(23.25, "2025-01-07T12:00:00Z"))

        self.assertEqual(result.payload["metrics"]["vix"]["delta"], 3.25)
        self.assertTrue(result.intraday_appended)
        self.assertFalse(result.weekly_appended)

    def test_duplicate_source_timestamp_changes_no_files(self) -> None:
        snapshot = self.snapshot(20.0, "2025-01-06T12:00:00Z")
        self.store.update(snapshot)
        before = self.latest_path.read_bytes()

        result = self.store.update(snapshot)

        self.assertFalse(result.changed)
        self.assertEqual(self.latest_path.read_bytes(), before)

    def test_weekly_backfill_is_merged_and_pruned_to_retention(self) -> None:
        snapshot = self.snapshot(20.0, "2025-01-06T12:00:00Z")
        snapshot["weekly_history"] = [
            {"as_of": "2010-01-08T00:00:00Z", "close": 80.0, "cci": 1.0, "rsi": 50.0},
            {"as_of": "2025-01-03T00:00:00Z", "close": 100.0, "cci": 25.0, "rsi": 55.0},
        ]

        self.store.update(snapshot)

        weekly = json.loads(
            (self.history_dir / "weekly.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(weekly["observations"]), 1)
        self.assertEqual(weekly["observations"][0]["close"], 100.0)

    def test_malformed_existing_history_is_not_overwritten(self) -> None:
        self.history_dir.mkdir(parents=True)
        path = self.history_dir / "intraday.json"
        path.write_text("not json", encoding="utf-8")

        with self.assertRaises(StorageError):
            self.store.update(self.snapshot(20.0, "2025-01-06T12:00:00Z"))
        self.assertEqual(path.read_text(encoding="utf-8"), "not json")


if __name__ == "__main__":
    unittest.main()
