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


class DatasetRef(BaseModel):
    path: str
    format: str
    rows: int
    size_bytes: int
    columns: list[str] = Field(default_factory=list)
    fingerprint: str


class OverlapStats(BaseModel):
    shared_records: int
    only_in_a: int
    only_in_b: int


class CompareReport(BaseModel):
    """Machine-readable comparison of two datasets."""

    tool: str = "rupudata"
    version: str
    dataset_a: DatasetRef
    dataset_b: DatasetRef
    exact_overlap: OverlapStats
    normalized_overlap: OverlapStats
    notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
