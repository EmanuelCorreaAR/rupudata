"""Structured models for technical audit contracts.

Reports follow: input → configuration → method → result.
This is reproducible technical evidence, not legal certification.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

DISCLAIMER = "Technical signals, not legal certification."
CONTRACT_ID = "technical_audit"

# Shared vocabulary across scan / compare / benchmark-check
FINGERPRINT_METHOD_ID = "normalized_record_multiset_sha256"
ROW_INDEX_BASE_DEFAULT = 0
DEFAULT_MAX_EVIDENCE_PAIRS = 100

NOTE_CONTRACT = (
    "This report is a technical audit contract (input → configuration → method → result)."
)
NOTE_TECHNICAL_SIGNALS = "RupuData provides technical signals, not legal certification."
NOTE_NOT_CONTAMINATION = (
    "Findings are technical evidence under the configured methodology "
    "— not a legal or scientific contamination verdict."
)
NOTE_ROW_INDICES = "Row indices in evidence (when present) are 0-based."

# Matching unit categories (method.unit)
UNIT_FULL_RECORD = "full_record"
UNIT_FIELD_TEXT = "field_text"
UNIT_EXTRACTED_TEXT = "extracted_text"


class GateRule(BaseModel):
    """One quality-policy threshold check (actual <= threshold passes)."""

    metric: str
    threshold: float
    actual: float
    passed: bool


class GateResult(BaseModel):
    """Aggregated policy decision when CI gates were configured."""

    passed: bool
    rules: list[GateRule] = Field(default_factory=list)


class MinHashInfo(BaseModel):
    """Whether MinHash/LSH was actually used for candidate generation."""

    enabled: bool
    num_perm: Optional[int] = None


class RecordNormalizationSpec(BaseModel):
    """Explicit transforms applied before hashing a full record.

    Used by fingerprint and exact-duplicate hashing in ``scan``, and by
    normalized overlap in ``compare``.
    """

    id: str = "record_normalized_v1"
    includes_all_fields: bool = True
    sort_object_keys: bool = True
    string_strip: bool = True
    collapse_internal_whitespace: bool = False
    case_fold: bool = False
    unicode_normalize: Optional[str] = None
    serialization: str = "json_utf8_compact_sorted_keys"
    hash: str = "sha256"
    notes: list[str] = Field(
        default_factory=lambda: [
            'Strings: only str.strip() (leading/trailing whitespace).',
            '" Hello   World " becomes "Hello   World" (internal spaces kept).',
            "No lowercasing, no Unicode NFC/NFKC, no column exclusions.",
        ]
    )


class RecordExactSpec(BaseModel):
    """Stable serialization without string stripping (compare exact overlap)."""

    id: str = "record_exact_v1"
    includes_all_fields: bool = True
    sort_object_keys: bool = True
    string_strip: bool = False
    collapse_internal_whitespace: bool = False
    case_fold: bool = False
    unicode_normalize: Optional[str] = None
    serialization: str = "json_utf8_compact_sorted_keys"
    hash: str = "sha256"
    notes: list[str] = Field(
        default_factory=lambda: [
            "Strings are left unchanged (no strip).",
            "Object keys are sorted for stable JSON only.",
        ]
    )


class NearDuplicateTextPrepSpec(BaseModel):
    """Text preparation used only for near-duplicate shingling (not fingerprint)."""

    id: str = "near_text_v1"
    prefer_text_column: bool = True
    fallback: str = "join_sorted_string_fields"
    lowercase: bool = True
    collapse_whitespace: bool = True
    notes: list[str] = Field(
        default_factory=lambda: [
            "Applies only to near-duplicate lexical similarity.",
            "Does not affect fingerprint or exact-duplicate hashes.",
        ]
    )


class TextExactSpec(BaseModel):
    """How a plain text value is hashed without strip (text matching).

    String transforms match ``record_exact_v1``. The *source* of the text
    (explicit field vs benchmark text_extraction) is declared on ``method``,
    not in this spec.
    """

    id: str = "text_exact_v1"
    base_normalization: str = "record_exact_v1"
    string_strip: bool = False
    collapse_internal_whitespace: bool = False
    case_fold: bool = False
    unicode_normalize: Optional[str] = None
    serialization: str = "json_utf8_compact_sorted_keys_on_{text}"
    hash: str = "sha256"
    notes: list[str] = Field(
        default_factory=lambda: [
            "Defines transforms + hash for one plain text value.",
            "base_normalization names the full-record spec whose string transforms are reused.",
            "Text source is declared by the command method (field_text or text_extraction).",
        ]
    )


class TextNormalizedSpec(BaseModel):
    """How a plain text value is hashed with strip (text matching).

    String transforms match ``record_normalized_v1``. The *source* of the text
    is declared on ``method``, not in this spec.
    """

    id: str = "text_normalized_v1"
    base_normalization: str = "record_normalized_v1"
    string_strip: bool = True
    collapse_internal_whitespace: bool = False
    case_fold: bool = False
    unicode_normalize: Optional[str] = None
    serialization: str = "json_utf8_compact_sorted_keys_on_{text}"
    hash: str = "sha256"
    notes: list[str] = Field(
        default_factory=lambda: [
            "Defines transforms + hash for one plain text value.",
            "base_normalization names the full-record spec whose string transforms are reused.",
            "Text source is declared by the command method (field_text or text_extraction).",
        ]
    )


RECORD_NORMALIZATION_V1 = RecordNormalizationSpec()
RECORD_EXACT_V1 = RecordExactSpec()
NEAR_TEXT_PREP_V1 = NearDuplicateTextPrepSpec()
TEXT_EXACT_V1 = TextExactSpec()
TEXT_NORMALIZED_V1 = TextNormalizedSpec()


# --- scan ------------------------------------------------------------------


class ScanInput(BaseModel):
    path: str
    format: str
    rows: int
    size_bytes: int
    columns: list[str] = Field(default_factory=list)


class ShingleSpec(BaseModel):
    """Shingle definition used for near-duplicate Jaccard similarity."""

    unit: str = "character"
    size: int = 5


class NearDuplicateConfiguration(BaseModel):
    """Requested near-duplicate settings (CLI/config intent)."""

    enabled: bool = True
    threshold: float
    shingle: ShingleSpec
    num_perm: int
    max_evidence_pairs: int = DEFAULT_MAX_EVIDENCE_PAIRS


class ScanConfiguration(BaseModel):
    row_index_base: int = ROW_INDEX_BASE_DEFAULT
    near_duplicates: NearDuplicateConfiguration
    max_duplicate_rate: Optional[float] = None
    max_near_duplicate_rate: Optional[float] = None


class NearDuplicateMethod(BaseModel):
    similarity: str = "character_shingles+jaccard"
    candidate_generation: str
    shingle: ShingleSpec = Field(default_factory=ShingleSpec)
    minhash: MinHashInfo
    text_prep: NearDuplicateTextPrepSpec = Field(default_factory=NearDuplicateTextPrepSpec)


class ScanMethod(BaseModel):
    unit: str = UNIT_FULL_RECORD
    fingerprint: str = FINGERPRINT_METHOD_ID
    exact_duplicates: str = (
        "record_normalized_v1 / normalized_record_sha256 "
        "(NOT compare exact_overlap / record_exact_v1)"
    )
    row_index_base: int = ROW_INDEX_BASE_DEFAULT
    record_normalized: RecordNormalizationSpec = Field(
        default_factory=RecordNormalizationSpec
    )
    near_duplicates: NearDuplicateMethod


class ExactDuplicateResult(BaseModel):
    """Exact-duplicate finding (count ≡ duplicate_records)."""

    total_records: int
    unique_records: int
    duplicate_records: int
    duplicate_rate: float


class NearDuplicateEvidenceItem(BaseModel):
    """One near-duplicate pair for audit evidence (0-based row indices)."""

    left: int
    right: int
    jaccard: float
    field: Optional[str] = None


class NearDuplicateResult(BaseModel):
    """Near-duplicate finding (count ≡ pairs; rate ≡ record_rate)."""

    pairs: int
    records_flagged: int
    record_rate: float
    evidence: list[NearDuplicateEvidenceItem] = Field(default_factory=list)
    evidence_truncated: bool = False


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
    gate: Optional[GateResult] = None
    notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


# --- compare ---------------------------------------------------------------


class DatasetRef(BaseModel):
    path: str
    format: str
    rows: int
    size_bytes: int
    columns: list[str] = Field(default_factory=list)
    fingerprint: str


class OverlapStats(BaseModel):
    """Overlap finding for one match mode (count ≡ shared_records).

    ``rate`` = shared_records / min(unique_a, unique_b) where
    unique_* = shared_records + only_in_*.
    """

    shared_records: int
    only_in_a: int
    only_in_b: int
    rate: float = 0.0


class CompareInput(BaseModel):
    dataset_a: DatasetRef
    dataset_b: DatasetRef


class CompareConfiguration(BaseModel):
    match_exact: bool = True
    match_normalized: bool = True
    max_evidence_pairs: int = DEFAULT_MAX_EVIDENCE_PAIRS
    row_index_base: int = ROW_INDEX_BASE_DEFAULT
    field: Optional[str] = None
    max_overlap_rate: Optional[float] = None
    fail_on_overlap: bool = False


class CompareMethod(BaseModel):
    unit: str = UNIT_FULL_RECORD
    field: Optional[str] = None
    exact_overlap: str = "record_exact_v1"
    normalized_overlap: str = "record_normalized_v1"
    fingerprint: str = FINGERPRINT_METHOD_ID
    row_index_base: int = ROW_INDEX_BASE_DEFAULT
    field_diff: Optional[str] = None
    record_exact: Optional[RecordExactSpec] = Field(default_factory=RecordExactSpec)
    record_normalized: Optional[RecordNormalizationSpec] = Field(
        default_factory=RecordNormalizationSpec
    )
    text_exact: Optional[TextExactSpec] = None
    text_normalized: Optional[TextNormalizedSpec] = None


class FieldDiff(BaseModel):
    field: str
    a: str
    b: str


class ValueDifference(BaseModel):
    a: str
    b: str


class CompareMatchItem(BaseModel):
    """One compare evidence pair (serialized with ``exclude_none``).

    Shape rules:
    - ``matches.exact``: row indices (+ ``field`` in field_text mode). No
      ``also_exact``, ``differing_fields``, or ``difference``.
    - ``matches.normalized``: always includes ``also_exact``. When
      ``also_exact`` is false, full_record adds ``differing_fields`` and
      field_text adds ``difference``; when true, both diffs are omitted.
    """

    dataset_a_record: int
    dataset_b_record: int
    field: Optional[str] = None
    also_exact: Optional[bool] = None
    differing_fields: Optional[list[FieldDiff]] = None
    difference: Optional[ValueDifference] = None


class CompareMatchEvidence(BaseModel):
    exact: list[CompareMatchItem] = Field(default_factory=list)
    normalized: list[CompareMatchItem] = Field(default_factory=list)
    exact_truncated: bool = False
    normalized_truncated: bool = False


class CompareResult(BaseModel):
    exact_overlap: OverlapStats
    normalized_overlap: OverlapStats
    matches: CompareMatchEvidence = Field(default_factory=CompareMatchEvidence)


class CompareReport(BaseModel):
    """Machine-readable technical audit comparing two datasets."""

    tool: str = "rupudata"
    version: str
    contract: str = CONTRACT_ID
    disclaimer: str = DISCLAIMER
    input: CompareInput
    configuration: CompareConfiguration = Field(default_factory=CompareConfiguration)
    method: CompareMethod = Field(default_factory=CompareMethod)
    result: CompareResult
    gate: Optional[GateResult] = None
    notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


# --- benchmark-check -------------------------------------------------------


class BenchmarkInput(BaseModel):
    dataset: DatasetRef
    benchmark_id: str
    benchmark_name: str
    reference_source: str
    reference_path: str
    benchmark_records: int
    benchmark_fingerprint: str


class BenchmarkConfiguration(BaseModel):
    benchmark: str
    match_exact: bool = True
    match_normalized: bool = True
    match_near_duplicate: bool = False
    max_evidence_pairs: int = DEFAULT_MAX_EVIDENCE_PAIRS
    row_index_base: int = ROW_INDEX_BASE_DEFAULT
    max_overlap_rate: Optional[float] = None
    fail_on_overlap: bool = False


class TextExtractionSpec(BaseModel):
    """How one plain text value is chosen per record (benchmark text source)."""

    strategy: str = "first_non_empty"
    candidate_fields: list[str] = Field(
        default_factory=lambda: ["question", "problem", "prompt", "text"]
    )


class BenchmarkMethod(BaseModel):
    unit: str = UNIT_EXTRACTED_TEXT
    text_extraction: TextExtractionSpec = Field(default_factory=TextExtractionSpec)
    fingerprint: str = FINGERPRINT_METHOD_ID
    row_index_base: int = ROW_INDEX_BASE_DEFAULT
    exact: str = "text_exact_v1"
    normalized: str = "text_normalized_v1"
    near_duplicate: str = "disabled"
    text_exact: TextExactSpec = Field(default_factory=TextExactSpec)
    text_normalized: TextNormalizedSpec = Field(default_factory=TextNormalizedSpec)


class MatchEvidenceItem(BaseModel):
    dataset_record: int
    reference_record: int
    field: str


class MatchEvidence(BaseModel):
    exact: list[MatchEvidenceItem] = Field(default_factory=list)
    normalized: list[MatchEvidenceItem] = Field(default_factory=list)
    exact_truncated: bool = False
    normalized_truncated: bool = False


class BenchmarkResult(BaseModel):
    """Benchmark overlap finding (count ≡ *_matches; rates vs dataset_rows)."""

    exact_matches: int
    normalized_matches: int
    near_matches: int = 0
    exact_rate: float = 0.0
    normalized_rate: float = 0.0
    status: str
    matches: MatchEvidence = Field(default_factory=MatchEvidence)


class BenchmarkCheckReport(BaseModel):
    """Technical audit of dataset vs benchmark text overlap."""

    tool: str = "rupudata"
    version: str
    contract: str = CONTRACT_ID
    disclaimer: str = DISCLAIMER
    input: BenchmarkInput
    configuration: BenchmarkConfiguration
    method: BenchmarkMethod
    result: BenchmarkResult
    gate: Optional[GateResult] = None
    notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)
