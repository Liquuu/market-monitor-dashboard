from __future__ import annotations

from pathlib import Path
import unittest

import yaml


class WorkflowTests(unittest.TestCase):
    def load(self, name: str) -> dict[str, object]:
        path = Path(".github/workflows") / name
        return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    def test_intraday_schedule_uses_japan_timezone(self) -> None:
        workflow = self.load("update-intraday.yml")
        schedule = workflow["on"]["schedule"][0]

        self.assertEqual(schedule["cron"], "0 9,21 * * *")
        self.assertEqual(schedule["timezone"], "Asia/Tokyo")
        self.assertEqual(workflow["permissions"]["contents"], "write")

    def test_weekly_schedule_uses_japan_timezone(self) -> None:
        workflow = self.load("update-weekly.yml")
        schedule = workflow["on"]["schedule"][0]

        self.assertEqual(schedule["cron"], "0 8 * * 1")
        self.assertEqual(schedule["timezone"], "Asia/Tokyo")


if __name__ == "__main__":
    unittest.main()
