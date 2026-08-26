"""Persistent JSON history and latest-snapshot management."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import pandas as pd

from .config import StorageConfig


class StorageError(RuntimeError):
    """Raised when existing dashboard data is malformed or unreadable."""


@dataclass(frozen=True, slots=True)
class UpdateResult:
    payload: dict[str, Any]
    intraday_appended: bool
    weekly_appended: bool

    @property
    def changed(self) -> bool:
        return self.intraday_appended or self.weekly_appended


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Replace a JSON file atomically so a failed run cannot truncate it."""

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


def _read_mapping(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(f"Unable to read valid JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise StorageError(f"Expected a JSON object in {path}")
    return value


def _history_document(path: Path) -> dict[str, Any]:
    document = _read_mapping(
        path, {"schema_version": 1, "updated_at": None, "observations": []}
    )
    observations = document.get("observations")
    if not isinstance(observations, list):
        raise StorageError(f"observations must be a list in {path}")
    return document


def _prune(
    observations: list[dict[str, Any]],
    *,
    timestamp_key: str,
    years: int,
    now: str,
) -> list[dict[str, Any]]:
    cutoff = pd.Timestamp(now) - pd.DateOffset(years=years)
    kept: list[dict[str, Any]] = []
    for observation in observations:
        try:
            timestamp = pd.Timestamp(observation[timestamp_key])
            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize("UTC")
            else:
                timestamp = timestamp.tz_convert("UTC")
        except (KeyError, TypeError, ValueError) as error:
            raise StorageError(
                f"Invalid {timestamp_key} in a history observation"
            ) from error
        if timestamp >= cutoff:
            kept.append(observation)
    return kept


class DashboardStore:
    def __init__(
        self, latest_path: Path, history_dir: Path, config: StorageConfig
    ) -> None:
        self.latest_path = latest_path
        self.intraday_path = history_dir / "intraday.json"
        self.weekly_path = history_dir / "weekly.json"
        self.config = config

    def _latest(self) -> dict[str, Any]:
        return _read_mapping(
            self.latest_path,
            {
                "schema_version": 1,
                "mode": "sample",
                "generated_at": None,
                "status": {"state": "setup", "message": "データ取得前です。"},
                "metrics": {},
                "weekly": {"as_of": None, "cci": None, "rsi": None},
            },
        )

    def needs_weekly_bootstrap(self) -> bool:
        weekly = self._latest().get("weekly")
        return not isinstance(weekly, dict) or weekly.get("as_of") is None

    @staticmethod
    def _intraday_duplicate(
        current: dict[str, dict[str, Any]], previous: dict[str, Any] | None
    ) -> bool:
        if not previous:
            return False
        previous_metrics = previous.get("metrics")
        if not isinstance(previous_metrics, dict) or set(previous_metrics) != set(current):
            return False
        return all(
            previous_metrics[key].get("observed_at") == metric.get("observed_at")
            for key, metric in current.items()
        )

    @staticmethod
    def _add_deltas(
        current: dict[str, dict[str, Any]], previous: dict[str, Any] | None
    ) -> dict[str, dict[str, Any]]:
        previous_metrics = previous.get("metrics", {}) if previous else {}
        with_deltas: dict[str, dict[str, Any]] = {}
        for key, metric in current.items():
            item = dict(metric)
            prior = previous_metrics.get(key, {})
            prior_value = prior.get("value") if isinstance(prior, dict) else None
            value = item.get("value")
            if isinstance(value, (int, float)) and isinstance(prior_value, (int, float)):
                decimals = item.get("decimals", 2)
                item["delta"] = round(float(value) - float(prior_value), decimals)
            else:
                item["delta"] = None
            with_deltas[key] = item
        return with_deltas

    @staticmethod
    def _compact_metrics(metrics: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {
            key: {
                "value": metric.get("value"),
                "observed_at": metric.get("observed_at"),
            }
            for key, metric in metrics.items()
        }

    @staticmethod
    def _complete(latest: dict[str, Any]) -> bool:
        metrics = latest.get("metrics")
        weekly = latest.get("weekly")
        metrics_ready = (
            isinstance(metrics, dict)
            and bool(metrics)
            and all(
                isinstance(metric, dict) and metric.get("value") is not None
                for metric in metrics.values()
            )
        )
        weekly_ready = isinstance(weekly, dict) and all(
            weekly.get(key) is not None for key in ("as_of", "cci", "rsi")
        )
        return metrics_ready and weekly_ready

    def update(self, snapshot: dict[str, Any]) -> UpdateResult:
        """Merge one or both snapshot sections and append non-duplicate history."""

        generated_at = snapshot.get("generated_at")
        if not isinstance(generated_at, str):
            raise StorageError("snapshot.generated_at must be an ISO timestamp")

        latest = self._latest()
        intraday_document = _history_document(self.intraday_path)
        weekly_document = _history_document(self.weekly_path)
        intraday_appended = False
        weekly_appended = False

        if "metrics" in snapshot:
            current_metrics = snapshot["metrics"]
            if not isinstance(current_metrics, dict) or not current_metrics:
                raise StorageError("snapshot.metrics must be a non-empty mapping")
            observations = intraday_document["observations"]
            previous = observations[-1] if observations else None
            duplicate = self.config.skip_duplicate_source_timestamp and self._intraday_duplicate(
                current_metrics, previous
            )
            if not duplicate:
                metrics_with_deltas = self._add_deltas(current_metrics, previous)
                observations.append(
                    {
                        "captured_at": generated_at,
                        "metrics": self._compact_metrics(metrics_with_deltas),
                    }
                )
                intraday_document["observations"] = _prune(
                    observations,
                    timestamp_key="captured_at",
                    years=self.config.intraday_history_years,
                    now=generated_at,
                )
                intraday_document["updated_at"] = generated_at
                latest["metrics"] = metrics_with_deltas
                intraday_appended = True

        if "weekly" in snapshot:
            current_weekly = snapshot["weekly"]
            if not isinstance(current_weekly, dict) or not current_weekly.get("as_of"):
                raise StorageError("snapshot.weekly must contain as_of")
            observations = weekly_document["observations"]
            candidates = snapshot.get("weekly_history", [current_weekly])
            if not isinstance(candidates, list) or not candidates:
                raise StorageError("snapshot.weekly_history must be a non-empty list")
            for candidate in candidates:
                if not isinstance(candidate, dict) or not candidate.get("as_of"):
                    raise StorageError("weekly history entries must contain as_of")

            merged = {
                observation.get("as_of"): observation for observation in observations
            }
            for candidate in candidates:
                merged[candidate["as_of"]] = dict(candidate)
            merged_observations = sorted(merged.values(), key=lambda item: item["as_of"])
            merged_observations = _prune(
                merged_observations,
                timestamp_key="as_of",
                years=self.config.weekly_history_years,
                now=generated_at,
            )
            latest_weekly_changed = latest.get("weekly") != current_weekly
            history_changed = merged_observations != observations
            if latest_weekly_changed or history_changed:
                weekly_document["observations"] = merged_observations
                weekly_document["updated_at"] = generated_at
                latest["weekly"] = dict(current_weekly)
                weekly_appended = True

        result = UpdateResult(latest, intraday_appended, weekly_appended)
        if not result.changed:
            return result

        latest["schema_version"] = 1
        latest["generated_at"] = generated_at
        if self._complete(latest):
            latest["mode"] = "live"
            latest["status"] = {
                "state": "ready",
                "message": "市場データを正常に取得しました。",
            }
        else:
            latest["mode"] = "partial"
            latest["status"] = {
                "state": "setup",
                "message": "一部のデータを取得しました。残りの定期処理を待っています。",
            }

        if intraday_appended:
            write_json_atomic(self.intraday_path, intraday_document)
        if weekly_appended:
            write_json_atomic(self.weekly_path, weekly_document)
        write_json_atomic(self.latest_path, latest)
        return result
