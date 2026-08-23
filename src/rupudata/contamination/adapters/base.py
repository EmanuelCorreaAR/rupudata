"""Benchmark adapter protocol — pluggable reference loaders for benchmark-check."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import polars as pl


@dataclass(frozen=True)
class ReferenceLoad:
    """Loaded benchmark reference plus provenance for the audit contract."""

    frame: pl.DataFrame
    source: str
    path: str


@runtime_checkable
class BenchmarkAdapter(Protocol):
    id: str
    name: str
    description: str
    notes: tuple[str, ...]

    def candidate_fields(self) -> list[str]:
        """Ordered candidate field names for text extraction (first_non_empty)."""

    def load_reference(self, reference: Path | None = None) -> ReferenceLoad:
        """Load packaged sample or user-supplied reference dataset."""
