"""Benchmark overlap matching (technical evidence, not contamination claims)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import polars as pl

from rupudata.core.normalization import hash_record, hash_record_exact
from rupudata.core.reader import read_dataset


def extract_comparable_text(
    record: dict[str, Any],
    fields: Sequence[str],
) -> str | None:
    """Extract text from the first non-empty field in ``fields`` order."""
    for key in fields:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _text_record(text: str) -> dict[str, str]:
    return {"text": text}


def unique_text_hashes(
    df: pl.DataFrame,
    *,
    normalized: bool,
    fields: Sequence[str],
) -> set[str]:
    hasher = hash_record if normalized else hash_record_exact
    hashes: set[str] = set()
    for row in df.iter_rows(named=True):
        text = extract_comparable_text(row, fields)
        if text is None:
            continue
        hashes.add(hasher(_text_record(text)))
    return hashes


def count_overlap(dataset_hashes: set[str], benchmark_hashes: set[str]) -> int:
    return len(dataset_hashes & benchmark_hashes)


def load_table(path: Path) -> pl.DataFrame:
    df, _ = read_dataset(path)
    return df
