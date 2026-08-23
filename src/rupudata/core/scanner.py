"""Orchestrate a dataset scan into a technical audit contract."""

from __future__ import annotations

from pathlib import Path

from rupudata import __version__
from rupudata.analyzers.duplicates import analyze_exact_duplicates
from rupudata.analyzers.near_duplicates import NearDuplicateConfig, analyze_near_duplicates
from rupudata.core.models import (
    NearDuplicateConfiguration,
    NearDuplicateMethod,
    NearDuplicateResult,
    ScanConfiguration,
    ScanInput,
    ScanMethod,
    ScanReport,
    ScanResult,
)
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

    exact = analyze_exact_duplicates(df)
    near = analyze_near_duplicates(df, cfg)
    fingerprint = fingerprint_dataframe(df)

    notes = [
        "This report is a technical audit contract (input → configuration → method → result).",
        "RupuData provides technical signals, not legal certification.",
        "Near-duplicates measure lexical similarity only — not paraphrases or translations.",
        "Provenance and benchmark adapters are not in this release.",
    ]
    if not cfg.enabled:
        notes = [
            "This report is a technical audit contract (input → configuration → method → result).",
            "RupuData provides technical signals, not legal certification.",
            "Near-duplicate detection was disabled for this scan.",
            "Provenance and benchmark adapters are not in this release.",
        ]
        near_method = NearDuplicateMethod(
            candidate_generation="disabled",
            minhash=near.method.minhash,
        )
        near_result = NearDuplicateResult(pairs=0, records_flagged=0, record_rate=0.0)
    else:
        near_method = near.method
        near_result = near.result

    return ScanReport(
        version=__version__,
        input=ScanInput(
            path=str(dataset_path),
            format=fmt.value,
            rows=df.height,
            size_bytes=file_size_bytes(dataset_path),
            columns=list(df.columns),
        ),
        configuration=ScanConfiguration(
            near_duplicates=NearDuplicateConfiguration(
                enabled=cfg.enabled,
                threshold=cfg.threshold,
                shingle_size=cfg.shingle_size,
                num_perm=cfg.num_perm,
            )
        ),
        method=ScanMethod(near_duplicates=near_method),
        result=ScanResult(
            fingerprint=fingerprint,
            exact_duplicates=exact,
            near_duplicates=near_result,
        ),
        notes=notes,
    )
