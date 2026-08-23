"""Dataset reading and format detection."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import polars as pl


class DatasetFormat(str, Enum):
    JSONL = "jsonl"
    PARQUET = "parquet"


SUPPORTED_SUFFIXES = {
    ".jsonl": DatasetFormat.JSONL,
    ".json": DatasetFormat.JSONL,
    ".parquet": DatasetFormat.PARQUET,
    ".pq": DatasetFormat.PARQUET,
}


def detect_format(path: Path) -> DatasetFormat:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise ValueError(
            f"Unsupported format for '{path.name}' "
            f"(suffix '{suffix}'). Supported: {supported}"
        )
    return SUPPORTED_SUFFIXES[suffix]


def read_dataset(path: Path) -> tuple[pl.DataFrame, DatasetFormat]:
    """Load a local dataset into a Polars DataFrame.

    MVP loads the full file. Streaming/chunked paths come later
    for large datasets.
    """
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    if not path.is_file():
        raise ValueError(f"Expected a file, got: {path}")

    fmt = detect_format(path)
    if fmt is DatasetFormat.JSONL:
        df = pl.read_ndjson(path)
    else:
        df = pl.read_parquet(path)

    return df, fmt


def file_size_bytes(path: Path) -> int:
    return path.stat().st_size
