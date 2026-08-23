"""Compare two datasets for exact and normalized record overlap."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from rupudata import __version__
from rupudata.core.models import (
    CompareInput,
    CompareReport,
    CompareResult,
    DatasetRef,
    OverlapStats,
)
from rupudata.core.normalization import (
    fingerprint_dataframe,
    hash_record_exact,
    hash_record_normalized,
)
from rupudata.core.reader import file_size_bytes, read_dataset


def _unique_hashes(df: pl.DataFrame, hasher) -> set[str]:
    return {hasher(row) for row in df.iter_rows(named=True)}


def _overlap_stats(hashes_a: set[str], hashes_b: set[str]) -> OverlapStats:
    shared = hashes_a & hashes_b
    return OverlapStats(
        shared_records=len(shared),
        only_in_a=len(hashes_a - hashes_b),
        only_in_b=len(hashes_b - hashes_a),
    )


def _dataset_ref(path: Path, df: pl.DataFrame, fmt: str) -> DatasetRef:
    return DatasetRef(
        path=str(path),
        format=fmt,
        rows=df.height,
        size_bytes=file_size_bytes(path),
        columns=list(df.columns),
        fingerprint=fingerprint_dataframe(df),
    )


def compare_datasets(path_a: str | Path, path_b: str | Path) -> CompareReport:
    """Compare two local datasets by record-hash overlap.

    Exact overlap uses stable serialization without string stripping.
    Normalized overlap applies light normalization (e.g. strip) first.

    This reports technical overlap under those methods — not semantic
    contamination, paraphrases, or translations.
    """
    a_path = Path(path_a).expanduser().resolve()
    b_path = Path(path_b).expanduser().resolve()

    df_a, fmt_a = read_dataset(a_path)
    df_b, fmt_b = read_dataset(b_path)

    exact_a = _unique_hashes(df_a, hash_record_exact)
    exact_b = _unique_hashes(df_b, hash_record_exact)
    norm_a = _unique_hashes(df_a, hash_record_normalized)
    norm_b = _unique_hashes(df_b, hash_record_normalized)

    ref_a = _dataset_ref(a_path, df_a, fmt_a.value)
    ref_b = _dataset_ref(b_path, df_b, fmt_b.value)

    return CompareReport(
        version=__version__,
        input=CompareInput(dataset_a=ref_a, dataset_b=ref_b),
        configuration={},
        result=CompareResult(
            exact_overlap=_overlap_stats(exact_a, exact_b),
            normalized_overlap=_overlap_stats(norm_a, norm_b),
        ),
        notes=[
            "This report is a technical audit contract (input → configuration → method → result).",
            "Overlap counts unique records shared by both datasets under each hashing method.",
            "Normalized overlap strips leading/trailing whitespace in strings; exact does not.",
            "This is technical overlap evidence, not a claim of benchmark contamination.",
            "Paraphrases, translations, and semantic near-matches are not detected.",
        ],
    )
