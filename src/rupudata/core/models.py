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
NOTE_EXACT_VOCABULARY = (
    "Matching units are command-specific: "
    "scan exact_duplicates → record_normalized_v1; "
    "compare exact_overlap → record_exact_v1; "
    "compare normalized_overlap → record_normalized_v1; "
    "benchmark-check exact/normalized → text_exact_v1 / text_normalized_v1 "
    "(extracted comparison text after text_extraction). "
    "The word 'exact' does not mean the same operation in every command."
)


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
    """Exact hash of one extracted comparison text (no strip).

    Same string transforms as ``record_exact_v1``, but the unit is the text
    chosen by ``text_extraction`` (not the full record).
    """

    id: str = "text_exact_v1"
    unit: str = "extracted_comparison_text"
    string_strip: bool = False
    collapse_internal_whitespace: bool = False
    case_fold: bool = False
    unicode_normalize: Optional[str] = None
    serialization: str = "json_utf8_compact_sorted_keys_on_{text}"
    hash: str = "sha256"
    notes: list[str] = Field(
        default_factory=lambda: [
            "Applies after text_extraction (one text per record).",
            "String transforms match record_exact_v1; unit is not the full record.",
        ]
    )


class TextNormalizedSpec(BaseModel):
    """Normalized hash of one extracted comparison text (strip only).

    Same string transforms as ``record_normalized_v1``, but the unit is the
    text chosen by ``text_extraction`` (not the full record).
    """

    id: str = "text_normalized_v1"
    unit: str = "extracted_comparison_text"
    string_strip: bool = True
    collapse_internal_whitespace: bool = False
    case_fold: bool = False
    unicode_normalize: Optional[str] = None
    serialization: str = "json_utf8_compact_sorted_keys_on_{text}"
    hash: str = "sha256"
    notes: list[str] = Field(
        default_factory=lambda: [
            "Applies after text_extraction (one text per record).",
            "String transforms match record_normalized_v1; unit is not the full record.",
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


class ScanConfiguration(BaseModel):
    row_index_base: int = ROW_INDEX_BASE_DEFAULT
    near_duplicates: NearDuplicateConfiguration


class NearDuplicateMethod(BaseModel):
    similarity: str = "character_shingles+jaccard"
    candidate_generation: str
    shingle: ShingleSpec = Field(default_factory=ShingleSpec)
    minhash: MinHashInfo
    text_prep: NearDuplicateTextPrepSpec = Field(default_factory=NearDuplicateTextPrepSpec)


class ScanMethod(BaseModel):
    fingerprint: str = FINGERPRINT_METHOD_ID
    exact_duplicates: str = (
        "record_normalized_v1 / normalized_record_sha256 "
        "(NOT compare exact_overlap / record_exact_v1)"
    )
    row_index_base: int = ROW_INDEX_BASE_DEFAULT
    record_normalization: RecordNormalizationSpec = Field(
        default_factory=RecordNormalizationSpec
    )
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


class CompareConfiguration(BaseModel):
    match_exact: bool = True
    match_normalized: bool = True
    max_evidence_pairs: int = DEFAULT_MAX_EVIDENCE_PAIRS
    row_index_base: int = ROW_INDEX_BASE_DEFAULT


class CompareMethod(BaseModel):
    unit: str = "full record (all fields); not text extraction"
    exact_overlap: str = "record_exact_v1 (stable_json_sha256_no_strip)"
    normalized_overlap: str = "record_normalized_v1 (stable_json_sha256_with_strip)"
    fingerprint: str = FINGERPRINT_METHOD_ID
    row_index_base: int = ROW_INDEX_BASE_DEFAULT
    field_diff: str = (
        "raw_equality per field; differing_fields only on normalized matches "
        "that are not also exact; display values truncated"
    )
    record_exact: RecordExactSpec = Field(default_factory=RecordExactSpec)
    record_normalization: RecordNormalizationSpec = Field(
        default_factory=RecordNormalizationSpec
    )


class FieldDiff(BaseModel):
    field: str
    a: str
    b: str


class CompareMatchItem(BaseModel):
    dataset_a_record: int
    dataset_b_record: int
    also_exact: Optional[bool] = None
    differing_fields: list[FieldDiff] = Field(default_factory=list)


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
    notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


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


class TextExtractionSpec(BaseModel):
    """How one comparison text is chosen per record before matching."""

    strategy: str = "first_non_empty"
    candidate_fields: list[str] = Field(
        default_factory=lambda: ["question", "problem", "prompt", "text"]
    )
    unit: str = "one comparison text per record"


class BenchmarkMethod(BaseModel):
    text_extraction: TextExtractionSpec = Field(default_factory=TextExtractionSpec)
    fingerprint: str = FINGERPRINT_METHOD_ID
    row_index_base: int = ROW_INDEX_BASE_DEFAULT
    exact: str = "text_exact_v1 (extracted comparison text, no strip)"
    normalized: str = "text_normalized_v1 (extracted comparison text, strip)"
    near_duplicate: str = "disabled"
    text_exact: TextExactSpec = Field(default_factory=TextExactSpec)
    text_normalization: TextNormalizedSpec = Field(default_factory=TextNormalizedSpec)


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
    exact_matches: int
    normalized_matches: int
    near_matches: int = 0
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
    notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
