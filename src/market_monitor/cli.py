"""Command-line entry point for generating data/latest.json."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

from .config import load_config
from .providers.yahoo import YahooFinanceProvider
from .service import SnapshotService


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the latest market snapshot")
    parser.add_argument("--config", default="config/config.yaml", type=Path)
    parser.add_argument("--output", default="data/latest.json", type=Path)
    parser.add_argument(
        "--stdout", action="store_true", help="also print the generated JSON"
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    provider = YahooFinanceProvider(config.yahoo_timeout_seconds, config.yahoo_retries)
    payload = SnapshotService(config, provider).build()
    _write_json_atomic(args.output, payload)
    if args.stdout:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
