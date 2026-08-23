"""Structured models for technical audit contracts.

Reports follow: input → configuration → method → result.
This is reproducible technical evidence, not legal certification.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

DISCLAIMER = "Technical signals, not legal certification."
CONTRACT_ID = "technical_audit"


class MinHashInfo(BaseModel):
    """Whether MinHash/LSH was actually used for candidate generation."""

    enabled: bool
    num_perm: Optional[int] = None


# --- scan ------------------------------------------------------------------


class ScanInput(BaseModel):
    path: str
    format: str
    rows: int
    size_bytes: int
    columns: list[str] = Field(default_factory=list)


class NearDuplicateConfiguration(BaseModel):
    """Requested near-duplicate settings (CLI/config intent)."""

    enabled: bool = True
    threshold: float
    shingle_size: int
    num_perm: int


class ScanConfiguration(BaseModel):
    near_duplicates: NearDuplicateConfiguration


class NearDuplicateMethod(BaseModel):
    similarity: str = "character_shingles+jaccard"
    candidate_generation: str
    minhash: MinHashInfo


class ScanMethod(BaseModel):
    fingerprint: str = "normalized_record_multiset_sha256"
    exact_duplicates: str = "normalized_record_sha256"
    near_duplicates: NearDuplicateMethod


class ExactDuplicateResult(BaseModel):
    total_records: int
    unique_records: int
    duplicate_records: int
    duplicate_rate: float


class NearDuplicateResult(BaseModel):
    pairs: int
    records_flagged: int
    record_rate: float


class ScanResult(BaseModel):
    fingerprint: str
    exact_duplicates: ExactDuplicateResult
    near_duplicates: NearDuplicateResult


class ScanReport(BaseModel):
    """Machine-readable technical audit for a single dataset scan."""

    tool: str = "rupudata"
    version: str
    contract: str = CONTRACT_ID
    disclaimer: str = DISCLAIMER
    input: ScanInput
    configuration: ScanConfiguration
    method: ScanMethod
    result: ScanResult
    notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


# --- compare ---------------------------------------------------------------


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


class CompareInput(BaseModel):
    dataset_a: DatasetRef
    dataset_b: DatasetRef


class CompareMethod(BaseModel):
    exact_overlap: str = "stable_json_sha256_no_strip"
    normalized_overlap: str = "stable_json_sha256_with_strip"
    fingerprint: str = "normalized_record_multiset_sha256"


class CompareResult(BaseModel):
    exact_overlap: OverlapStats
    normalized_overlap: OverlapStats


class CompareReport(BaseModel):
    """Machine-readable technical audit comparing two datasets."""

    tool: str = "rupudata"
    version: str
    contract: str = CONTRACT_ID
    disclaimer: str = DISCLAIMER
    input: CompareInput
    configuration: Dict[str, Any] = Field(default_factory=dict)
    method: CompareMethod = Field(default_factory=CompareMethod)
    result: CompareResult
    notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
