"""Load and validate the human-editable dashboard configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when the dashboard configuration is invalid."""


@dataclass(frozen=True, slots=True)
class InstrumentConfig:
    key: str
    label: str
    provider: str
    symbol: str
    unit: str
    decimals: int
    source_url: str


@dataclass(frozen=True, slots=True)
class WeeklyIndicatorConfig:
    instrument: str
    exclude_incomplete_week: bool
    rsi_period: int
    cci_period: int
    cci_constant: float


@dataclass(frozen=True, slots=True)
class DrawdownConfig:
    instrument: str
    price_field: str
    lookback_days: int | None


@dataclass(frozen=True, slots=True)
class DashboardConfig:
    timezone: str
    yahoo_timeout_seconds: int
    yahoo_retries: int
    instruments: dict[str, InstrumentConfig]
    weekly: WeeklyIndicatorConfig
    drawdown: DrawdownConfig


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{path} must be a mapping")
    return value


def _positive_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigError(f"{path} must be a positive integer")
    return value


def _required_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{path} must be a non-empty string")
    return value.strip()


def load_config(path: str | Path) -> DashboardConfig:
    """Load config.yaml and return the validated fields used by task 3."""

    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"Unable to read {config_path}: {error}") from error
    except yaml.YAMLError as error:
        raise ConfigError(f"Invalid YAML in {config_path}: {error}") from error

    root = _mapping(raw, "root")
    project = _mapping(root.get("project"), "project")
    providers = _mapping(root.get("providers"), "providers")
    yahoo = _mapping(providers.get("yahoo"), "providers.yahoo")
    instruments_raw = _mapping(root.get("instruments"), "instruments")

    instruments: dict[str, InstrumentConfig] = {}
    for key, value in instruments_raw.items():
        item = _mapping(value, f"instruments.{key}")
        decimals = item.get("decimals", 2)
        if isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
            raise ConfigError(f"instruments.{key}.decimals must be a non-negative integer")
        instruments[key] = InstrumentConfig(
            key=key,
            label=_required_text(item.get("label"), f"instruments.{key}.label"),
            provider=_required_text(item.get("provider"), f"instruments.{key}.provider"),
            symbol=_required_text(item.get("symbol"), f"instruments.{key}.symbol"),
            unit=_required_text(item.get("unit"), f"instruments.{key}.unit"),
            decimals=decimals,
            source_url=_required_text(item.get("source_url"), f"instruments.{key}.source_url"),
        )

    indicators = _mapping(root.get("indicators"), "indicators")
    weekly_raw = _mapping(indicators.get("weekly"), "indicators.weekly")
    rsi = _mapping(weekly_raw.get("rsi"), "indicators.weekly.rsi")
    cci = _mapping(weekly_raw.get("cci"), "indicators.weekly.cci")
    drawdown_raw = _mapping(indicators.get("drawdown"), "indicators.drawdown")

    weekly_instrument = _required_text(
        weekly_raw.get("instrument"), "indicators.weekly.instrument"
    )
    drawdown_instrument = _required_text(
        drawdown_raw.get("instrument"), "indicators.drawdown.instrument"
    )
    for instrument_key in {weekly_instrument, drawdown_instrument}:
        if instrument_key not in instruments:
            raise ConfigError(f"Unknown instrument referenced by indicators: {instrument_key}")

    lookback_days = drawdown_raw.get("lookback_days")
    if lookback_days is not None:
        lookback_days = _positive_int(lookback_days, "indicators.drawdown.lookback_days")

    cci_constant = cci.get("constant", 0.015)
    if isinstance(cci_constant, bool) or not isinstance(cci_constant, (int, float)) or cci_constant <= 0:
        raise ConfigError("indicators.weekly.cci.constant must be a positive number")

    return DashboardConfig(
        timezone=_required_text(project.get("timezone"), "project.timezone"),
        yahoo_timeout_seconds=_positive_int(
            yahoo.get("request_timeout_seconds", 30),
            "providers.yahoo.request_timeout_seconds",
        ),
        yahoo_retries=_positive_int(
            yahoo.get("retries", 3), "providers.yahoo.retries"
        ),
        instruments=instruments,
        weekly=WeeklyIndicatorConfig(
            instrument=weekly_instrument,
            exclude_incomplete_week=bool(weekly_raw.get("exclude_incomplete_week", True)),
            rsi_period=_positive_int(rsi.get("period"), "indicators.weekly.rsi.period"),
            cci_period=_positive_int(cci.get("period"), "indicators.weekly.cci.period"),
            cci_constant=float(cci_constant),
        ),
        drawdown=DrawdownConfig(
            instrument=drawdown_instrument,
            price_field=_required_text(
                drawdown_raw.get("price_field", "close"),
                "indicators.drawdown.price_field",
            ).capitalize(),
            lookback_days=lookback_days,
        ),
    )
