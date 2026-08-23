"""Orchestrate a dataset scan."""

from __future__ import annotations

from pathlib import Path

from rupudata import __version__
from rupudata.analyzers.duplicates import analyze_exact_duplicates
from rupudata.analyzers.near_duplicates import NearDuplicateConfig, analyze_near_duplicates
from rupudata.core.models import DatasetInfo, ScanReport
from rupudata.core.normalization import fingerprint_dataframe
from rupudata.core.reader import file_size_bytes, read_dataset


def scan_dataset(
    path: str | Path,
    *,
    near_config: NearDuplicateConfig | None = None,
) -> ScanReport:
    dataset_path = Path(path).expanduser().resolve()
    df, fmt = read_dataset(dataset_path)
    cfg = near_config or NearDuplicateConfig()

    info = DatasetInfo(
        path=str(dataset_path),
        format=fmt.value,
        rows=df.height,
        size_bytes=file_size_bytes(dataset_path),
        columns=list(df.columns),
        fingerprint=fingerprint_dataframe(df),
    )
    exact = analyze_exact_duplicates(df)
    near = analyze_near_duplicates(df, cfg)

    notes = [
        "RupuData provides technical signals, not legal certification.",
        "Near-duplicates use character shingles + Jaccard "
        f"(threshold={cfg.threshold}, shingle_size={cfg.shingle_size}); "
        "not paraphrases or translations.",
        "Provenance and benchmark adapters are not in this release.",
    ]
    if not cfg.enabled:
        notes = [
            "RupuData provides technical signals, not legal certification.",
            "Near-duplicate detection was disabled for this scan.",
            "Provenance and benchmark adapters are not in this release.",
        ]

    return ScanReport(
        version=__version__,
        dataset=info,
        exact_duplicates=exact,
        near_duplicates=near,
        notes=notes,
    )
