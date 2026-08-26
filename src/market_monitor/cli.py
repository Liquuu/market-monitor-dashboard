"""Command-line entry point for generating data/latest.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .providers.yahoo import YahooFinanceProvider
from .service import SnapshotService
from .storage import DashboardStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the latest market snapshot")
    parser.add_argument("--config", default="config/config.yaml", type=Path)
    parser.add_argument("--output", default="data/latest.json", type=Path)
    parser.add_argument("--history-dir", default="data/history", type=Path)
    parser.add_argument(
        "--scope",
        choices=("all", "intraday", "weekly"),
        default="all",
        help="select the data section to update",
    )
    parser.add_argument(
        "--stdout", action="store_true", help="also print the generated JSON"
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    provider = YahooFinanceProvider(config.yahoo_timeout_seconds, config.yahoo_retries)
    service = SnapshotService(config, provider)
    store = DashboardStore(args.output, args.history_dir, config.storage)

    snapshot: dict[str, object] = {}
    if args.scope in {"all", "intraday"}:
        snapshot.update(service.build_intraday())
    if args.scope in {"all", "weekly"} or (
        args.scope == "intraday" and store.needs_weekly_bootstrap()
    ):
        weekly = service.build_weekly()
        snapshot["weekly"] = weekly["weekly"]
        snapshot["weekly_history"] = weekly["weekly_history"]
        snapshot.setdefault("generated_at", weekly["generated_at"])

    result = store.update(snapshot)
    if args.stdout:
        print(json.dumps(result.payload, ensure_ascii=False, indent=2))
    if not result.changed:
        print("No new source timestamps; data files were left unchanged.")


if __name__ == "__main__":
    main()
