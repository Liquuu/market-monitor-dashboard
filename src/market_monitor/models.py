"""Shared data models for providers and calculation services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Quote:
    """A single observed market value."""

    value: float
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class DrawdownResult:
    """Drawdown calculated from a closing-price peak."""

    latest: float
    peak: float
    percent: float

