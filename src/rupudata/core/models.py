"""Structured models for scan results."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DatasetInfo(BaseModel):
    path: str
    format: str
    rows: int
    size_bytes: int
    columns: list[str] = Field(default_factory=list)
    fingerprint: str


class ExactDuplicates(BaseModel):
    total_records: int
    unique_records: int
    duplicate_records: int
    duplicate_rate: float


class ScanReport(BaseModel):
    """Machine-readable audit report for a single dataset scan."""

    tool: str = "rupudata"
    version: str
    dataset: DatasetInfo
    exact_duplicates: ExactDuplicates
    notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
