"""Orchestrate a dataset scan."""

from __future__ import annotations

from pathlib import Path

from rupudata import __version__
from rupudata.analyzers.duplicates import analyze_exact_duplicates
from rupudata.core.models import DatasetInfo, ScanReport
from rupudata.core.normalization import fingerprint_dataframe
from rupudata.core.reader import file_size_bytes, read_dataset


def scan_dataset(path: str | Path) -> ScanReport:
    dataset_path = Path(path).expanduser().resolve()
    df, fmt = read_dataset(dataset_path)

    info = DatasetInfo(
        path=str(dataset_path),
        format=fmt.value,
        rows=df.height,
        size_bytes=file_size_bytes(dataset_path),
        columns=list(df.columns),
        fingerprint=fingerprint_dataframe(df),
    )
    exact = analyze_exact_duplicates(df)

    return ScanReport(
        version=__version__,
        dataset=info,
        exact_duplicates=exact,
        notes=[
            "RupuData provides technical signals, not legal certification.",
            "Near-duplicate, provenance, and benchmark adapters are not in this release.",
        ],
    )
