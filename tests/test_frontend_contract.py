from __future__ import annotations

from pathlib import Path
import unittest


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = Path("index.html").read_text(encoding="utf-8")
        cls.javascript = Path("assets/js/app.js").read_text(encoding="utf-8")

    def test_chart_mount_points_exist(self) -> None:
        for element_id in ("cci-chart", "rsi-chart", "history-chart", "history-metric"):
            self.assertIn(f'id="{element_id}"', self.html)

    def test_frontend_loads_both_history_documents(self) -> None:
        self.assertIn("./data/history/weekly.json", self.javascript)
        self.assertIn("./data/history/intraday.json", self.javascript)

    def test_source_urls_are_protocol_checked(self) -> None:
        self.assertIn('includes(url.protocol)', self.javascript)


if __name__ == "__main__":
    unittest.main()
