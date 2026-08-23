"""Compare two datasets for exact and normalized overlap (record or field text)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from rupudata import __version__
from rupudata.core.models import (
    DEFAULT_MAX_EVIDENCE_PAIRS,
    FINGERPRINT_METHOD_ID,
    NOTE_CONTRACT,
    NOTE_EXACT_VOCABULARY,
    NOTE_NOT_CONTAMINATION,
    NOTE_ROW_INDICES,
    NOTE_TECHNICAL_SIGNALS,
    ROW_INDEX_BASE_DEFAULT,
    CompareConfiguration,
    CompareInput,
    CompareMatchEvidence,
    CompareMatchItem,
    CompareMethod,
    CompareReport,
    CompareResult,
    DatasetRef,
    FieldDiff,
    OverlapStats,
    RECORD_EXACT_V1,
    RECORD_NORMALIZATION_V1,
    TEXT_EXACT_V1,
    TEXT_NORMALIZED_V1,
    TextDifference,
)
from rupudata.core.normalization import (
    fingerprint_dataframe,
    hash_record_exact,
    hash_record_normalized,
)
from rupudata.core.reader import file_size_bytes, read_dataset

DEFAULT_MAX_EVIDENCE = DEFAULT_MAX_EVIDENCE_PAIRS
DEFAULT_VALUE_DISPLAY_MAX = 120
_MISSING = "<missing>"


@dataclass(frozen=True)
class RecordHit:
    row: int
    digest: str


@dataclass(frozen=True)
class RecordOverlapEvidence:
    unique_records: int
    only_in_a: int
    only_in_b: int
    pairs: list[CompareMatchItem]
    truncated: bool


def _index_records(df: pl.DataFrame, hasher) -> list[RecordHit]:
    return [
        RecordHit(row=idx, digest=hasher(row))
        for idx, row in enumerate(df.iter_rows(named=True))
    ]


def _index_text_field(df: pl.DataFrame, field: str, hasher) -> list[RecordHit]:
    hits: list[RecordHit] = []
    for idx, row in enumerate(df.iter_rows(named=True)):
        if field not in row or row[field] is None:
            continue
        hits.append(RecordHit(row=idx, digest=hasher({"text": str(row[field])})))
    return hits


def _build_record_overlap(
    hits_a: list[RecordHit],
    hits_b: list[RecordHit],
    *,
    max_pairs: int,
    field: str | None = None,
) -> RecordOverlapEvidence:
    by_hash_b: dict[str, list[RecordHit]] = defaultdict(list)
    for hit in hits_b:
        by_hash_b[hit.digest].append(hit)

    hashes_a = {h.digest for h in hits_a}
    hashes_b = set(by_hash_b)
    shared = hashes_a & hashes_b

    pairs: list[CompareMatchItem] = []
    truncated = False
    for a in hits_a:
        if a.digest not in shared:
            continue
        for b in by_hash_b[a.digest]:
            if len(pairs) >= max_pairs:
                truncated = True
                break
            pairs.append(
                CompareMatchItem(
                    dataset_a_record=a.row,
                    dataset_b_record=b.row,
                    field=field,
                )
            )
        if truncated:
            break

    return RecordOverlapEvidence(
        unique_records=len(shared),
        only_in_a=len(hashes_a - hashes_b),
        only_in_b=len(hashes_b - hashes_a),
        pairs=pairs,
        truncated=truncated,
    )


def _display_value(value: Any, *, max_len: int = DEFAULT_VALUE_DISPLAY_MAX) -> str:
    if value is None:
        text = "null"
    else:
        text = str(value)
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def field_diffs(
    record_a: dict[str, Any],
    record_b: dict[str, Any],
    *,
    max_len: int = DEFAULT_VALUE_DISPLAY_MAX,
) -> list[FieldDiff]:
    """Raw per-field inequality (no strip). Explains normalized-only full-record overlaps."""
    keys = sorted(set(record_a) | set(record_b))
    diffs: list[FieldDiff] = []
    for key in keys:
        in_a = key in record_a
        in_b = key in record_b
        if in_a and in_b and record_a[key] == record_b[key]:
            continue
        diffs.append(
            FieldDiff(
                field=key,
                a=_display_value(record_a[key], max_len=max_len) if in_a else _MISSING,
                b=_display_value(record_b[key], max_len=max_len) if in_b else _MISSING,
            )
        )
    return diffs


def _enrich_normalized_pairs(
    pairs: list[CompareMatchItem],
    *,
    rows_a: list[dict[str, Any]],
    rows_b: list[dict[str, Any]],
    exact_digest_a: dict[int, str],
    exact_digest_b: dict[int, str],
    text_field: str | None,
) -> list[CompareMatchItem]:
    enriched: list[CompareMatchItem] = []
    for pair in pairs:
        also_exact = (
            exact_digest_a[pair.dataset_a_record] == exact_digest_b[pair.dataset_b_record]
        )
        diffs: list[FieldDiff] = []
        text_diff: TextDifference | None = None
        if not also_exact:
            if text_field is None:
                diffs = field_diffs(
                    rows_a[pair.dataset_a_record],
                    rows_b[pair.dataset_b_record],
                )
            else:
                text_diff = TextDifference(
                    a=_display_value(rows_a[pair.dataset_a_record].get(text_field)),
                    b=_display_value(rows_b[pair.dataset_b_record].get(text_field)),
                )
        enriched.append(
            CompareMatchItem(
                dataset_a_record=pair.dataset_a_record,
                dataset_b_record=pair.dataset_b_record,
                field=text_field,
                also_exact=also_exact,
                differing_fields=diffs,
                text_difference=text_diff,
            )
        )
    return enriched


def _dataset_ref(path: Path, df: pl.DataFrame, fmt: str) -> DatasetRef:
    return DatasetRef(
        path=str(path),
        format=fmt,
        rows=df.height,
        size_bytes=file_size_bytes(path),
        columns=list(df.columns),
        fingerprint=fingerprint_dataframe(df),
    )


def _require_text_field(df: pl.DataFrame, path: Path, text_field: str) -> None:
    if text_field not in df.columns:
        raise ValueError(
            f"Column '{text_field}' not found in {path} "
            f"(available: {', '.join(df.columns)})"
        )


def compare_datasets(
    path_a: str | Path,
    path_b: str | Path,
    *,
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
    text_field: str | None = None,
) -> CompareReport:
    """Compare two local datasets by full-record or single-field text overlap.

    Default (``text_field=None``): full-record ``record_exact_v1`` /
    ``record_normalized_v1``.

    With ``text_field``: hash the named column via ``text_exact_v1`` /
    ``text_normalized_v1`` (unit ``field_text``). Same text transforms as
    record specs; source is the explicit field, not benchmark extraction.
    """
    a_path = Path(path_a).expanduser().resolve()
    b_path = Path(path_b).expanduser().resolve()

    df_a, fmt_a = read_dataset(a_path)
    df_b, fmt_b = read_dataset(b_path)

    if text_field is not None:
        _require_text_field(df_a, a_path, text_field)
        _require_text_field(df_b, b_path, text_field)

    rows_a = list(df_a.iter_rows(named=True))
    rows_b = list(df_b.iter_rows(named=True))

    if text_field is None:
        exact_a = _index_records(df_a, hash_record_exact)
        exact_b = _index_records(df_b, hash_record_exact)
        norm_a = _index_records(df_a, hash_record_normalized)
        norm_b = _index_records(df_b, hash_record_normalized)
    else:
        exact_a = _index_text_field(df_a, text_field, hash_record_exact)
        exact_b = _index_text_field(df_b, text_field, hash_record_exact)
        norm_a = _index_text_field(df_a, text_field, hash_record_normalized)
        norm_b = _index_text_field(df_b, text_field, hash_record_normalized)

    exact_ev = _build_record_overlap(
        exact_a, exact_b, max_pairs=max_evidence, field=text_field
    )
    norm_ev = _build_record_overlap(
        norm_a, norm_b, max_pairs=max_evidence, field=text_field
    )

    exact_digest_a = {h.row: h.digest for h in exact_a}
    exact_digest_b = {h.row: h.digest for h in exact_b}
    normalized_pairs = _enrich_normalized_pairs(
        norm_ev.pairs,
        rows_a=rows_a,
        rows_b=rows_b,
        exact_digest_a=exact_digest_a,
        exact_digest_b=exact_digest_b,
        text_field=text_field,
    )

    ref_a = _dataset_ref(a_path, df_a, fmt_a.value)
    ref_b = _dataset_ref(b_path, df_b, fmt_b.value)

    if text_field is None:
        method = CompareMethod(
            unit="full_record",
            text_field=None,
            exact_overlap="record_exact_v1 (stable_json_sha256_no_strip)",
            normalized_overlap="record_normalized_v1 (stable_json_sha256_with_strip)",
            fingerprint=FINGERPRINT_METHOD_ID,
            row_index_base=ROW_INDEX_BASE_DEFAULT,
            field_diff=(
                "raw_equality per field; differing_fields only on normalized matches "
                "that are not also exact; display values truncated"
            ),
            record_exact=RECORD_EXACT_V1,
            record_normalized=RECORD_NORMALIZATION_V1,
            text_exact=None,
            text_normalized=None,
        )
        notes = [
            NOTE_CONTRACT,
            NOTE_TECHNICAL_SIGNALS,
            NOTE_NOT_CONTAMINATION,
            NOTE_ROW_INDICES,
            NOTE_EXACT_VOCABULARY,
            "Pipeline: input → full-record hashing → exact/normalized matching → evidence → result.",
            "method.unit=full_record; overlap counts unique full records under record_* hashing.",
            "Normalized matches include also_exact; differing_fields only when also_exact is false.",
            "Paraphrases, translations, and semantic near-matches are not detected.",
        ]
    else:
        method = CompareMethod(
            unit="field_text",
            text_field=text_field,
            exact_overlap="text_exact_v1 (plain text value, no strip)",
            normalized_overlap="text_normalized_v1 (plain text value, strip)",
            fingerprint=FINGERPRINT_METHOD_ID,
            row_index_base=ROW_INDEX_BASE_DEFAULT,
            field_diff=None,
            record_exact=None,
            record_normalized=None,
            text_exact=TEXT_EXACT_V1,
            text_normalized=TEXT_NORMALIZED_V1,
        )
        notes = [
            NOTE_CONTRACT,
            NOTE_TECHNICAL_SIGNALS,
            NOTE_NOT_CONTAMINATION,
            NOTE_ROW_INDICES,
            NOTE_EXACT_VOCABULARY,
            "Pipeline: input → field text → text_exact/text_normalized matching → evidence → result.",
            f"method.unit=field_text; text source is the explicit column '{text_field}'.",
            "text_* specs define transforms; they do not define text extraction (benchmark uses text_extraction).",
            "Normalized matches include also_exact; text_difference only when also_exact is false.",
            "Paraphrases, translations, and semantic near-matches are not detected.",
        ]

    return CompareReport(
        version=__version__,
        input=CompareInput(dataset_a=ref_a, dataset_b=ref_b),
        configuration=CompareConfiguration(
            match_exact=True,
            match_normalized=True,
            max_evidence_pairs=max_evidence,
            row_index_base=ROW_INDEX_BASE_DEFAULT,
            text_field=text_field,
        ),
        method=method,
        result=CompareResult(
            exact_overlap=OverlapStats(
                shared_records=exact_ev.unique_records,
                only_in_a=exact_ev.only_in_a,
                only_in_b=exact_ev.only_in_b,
            ),
            normalized_overlap=OverlapStats(
                shared_records=norm_ev.unique_records,
                only_in_a=norm_ev.only_in_a,
                only_in_b=norm_ev.only_in_b,
            ),
            matches=CompareMatchEvidence(
                exact=exact_ev.pairs,
                normalized=normalized_pairs,
                exact_truncated=exact_ev.truncated,
                normalized_truncated=norm_ev.truncated,
            ),
        ),
        notes=notes,
    )
