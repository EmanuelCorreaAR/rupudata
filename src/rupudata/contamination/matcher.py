"""Benchmark overlap matching (technical evidence, not contamination claims)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import polars as pl

from rupudata.core.normalization import hash_record, hash_record_exact
from rupudata.core.reader import read_dataset

DEFAULT_MAX_EVIDENCE = 100


@dataclass(frozen=True)
class RowHit:
    row: int
    field: str
    digest: str


@dataclass(frozen=True)
class MatchHit:
    dataset_record: int
    reference_record: int
    field: str


@dataclass(frozen=True)
class OverlapEvidence:
    """Unique overlapping texts + concrete row/field pairs."""

    unique_texts: int
    pairs: list[MatchHit]
    truncated: bool


def extract_comparable(
    record: dict[str, Any],
    fields: Sequence[str],
) -> tuple[str, str] | None:
    """Return (field_name, raw_text) for the first non-empty field."""
    for key in fields:
        value = record.get(key)
        if value is not None and str(value).strip():
            return key, str(value)
    return None


def _text_record(text: str) -> dict[str, str]:
    return {"text": text}


def index_rows(
    df: pl.DataFrame,
    *,
    normalized: bool,
    fields: Sequence[str],
) -> list[RowHit]:
    hasher = hash_record if normalized else hash_record_exact
    hits: list[RowHit] = []
    for idx, row in enumerate(df.iter_rows(named=True)):
        extracted = extract_comparable(row, fields)
        if extracted is None:
            continue
        field, text = extracted
        hits.append(RowHit(row=idx, field=field, digest=hasher(_text_record(text))))
    return hits


def build_overlap_evidence(
    dataset_hits: list[RowHit],
    reference_hits: list[RowHit],
    *,
    max_pairs: int = DEFAULT_MAX_EVIDENCE,
) -> OverlapEvidence:
    by_hash_ref: dict[str, list[RowHit]] = defaultdict(list)
    for hit in reference_hits:
        by_hash_ref[hit.digest].append(hit)

    shared = {h.digest for h in dataset_hits} & set(by_hash_ref)
    pairs: list[MatchHit] = []
    truncated = False
    for ds in dataset_hits:
        if ds.digest not in shared:
            continue
        for ref in by_hash_ref[ds.digest]:
            if len(pairs) >= max_pairs:
                truncated = True
                break
            pairs.append(
                MatchHit(
                    dataset_record=ds.row,
                    reference_record=ref.row,
                    field=ds.field,
                )
            )
        if truncated:
            break

    return OverlapEvidence(
        unique_texts=len(shared),
        pairs=pairs,
        truncated=truncated,
    )


def load_table(path: Path) -> pl.DataFrame:
    df, _ = read_dataset(path)
    return df
