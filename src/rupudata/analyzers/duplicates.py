"""Exact duplicate detection."""

from __future__ import annotations

from collections import Counter

import polars as pl

from rupudata.core.models import ExactDuplicateResult
from rupudata.core.normalization import hash_record


def analyze_exact_duplicates(df: pl.DataFrame) -> ExactDuplicateResult:
    total = df.height
    if total == 0:
        return ExactDuplicateResult(
            total_records=0,
            unique_records=0,
            duplicate_records=0,
            duplicate_rate=0.0,
        )

    hashes = [hash_record(row) for row in df.iter_rows(named=True)]
    counts = Counter(hashes)
    unique = len(counts)
    duplicate_records = total - unique
    rate = duplicate_records / total if total else 0.0

    return ExactDuplicateResult(
        total_records=total,
        unique_records=unique,
        duplicate_records=duplicate_records,
        duplicate_rate=round(rate, 6),
    )
