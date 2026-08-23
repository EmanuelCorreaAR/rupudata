"""Orchestrate a dataset scan into a technical audit contract."""

from __future__ import annotations

from pathlib import Path

from rupudata import __version__
from rupudata.analyzers.duplicates import analyze_exact_duplicates
from rupudata.analyzers.near_duplicates import NearDuplicateConfig, analyze_near_duplicates
from rupudata.core.models import (
    NOTE_CONTRACT,
    NOTE_NOT_CONTAMINATION,
    NOTE_ROW_INDICES,
    NOTE_TECHNICAL_SIGNALS,
    NearDuplicateConfiguration,
    NearDuplicateMethod,
    NearDuplicateResult,
    RECORD_NORMALIZATION_V1,
    ROW_INDEX_BASE_DEFAULT,
    ScanConfiguration,
    ScanInput,
    ScanMethod,
    ScanReport,
    ScanResult,
    ShingleSpec,
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
    shingle = ShingleSpec(unit="character", size=cfg.shingle_size)

    exact = analyze_exact_duplicates(df)
    near = analyze_near_duplicates(df, cfg)
    fingerprint = fingerprint_dataframe(df)

    notes = [
        NOTE_CONTRACT,
        NOTE_TECHNICAL_SIGNALS,
        NOTE_NOT_CONTAMINATION,
        NOTE_ROW_INDICES,
        "Fingerprint and exact-duplicate hashes use record_normalized_v1 (full record).",
        "Near-duplicates measure lexical similarity only — not paraphrases or translations.",
    ]
    if not cfg.enabled:
        notes = [
            NOTE_CONTRACT,
            NOTE_TECHNICAL_SIGNALS,
            NOTE_NOT_CONTAMINATION,
            NOTE_ROW_INDICES,
            "Fingerprint and exact-duplicate hashes use record_normalized_v1 (full record).",
            "Near-duplicate detection was disabled for this scan.",
        ]
        near_method = NearDuplicateMethod(
            candidate_generation="disabled",
            shingle=shingle,
            minhash=near.method.minhash,
        )
        near_result = NearDuplicateResult(pairs=0, records_flagged=0, record_rate=0.0)
    else:
        near_method = NearDuplicateMethod(
            similarity=near.method.similarity,
            candidate_generation=near.method.candidate_generation,
            shingle=shingle,
            minhash=near.method.minhash,
            text_prep=near.method.text_prep,
        )
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
            row_index_base=ROW_INDEX_BASE_DEFAULT,
            near_duplicates=NearDuplicateConfiguration(
                enabled=cfg.enabled,
                threshold=cfg.threshold,
                shingle=shingle,
                num_perm=cfg.num_perm,
            ),
        ),
        method=ScanMethod(
            row_index_base=ROW_INDEX_BASE_DEFAULT,
            record_normalization=RECORD_NORMALIZATION_V1,
            near_duplicates=near_method,
        ),
        result=ScanResult(
            fingerprint=fingerprint,
            exact_duplicates=exact,
            near_duplicates=near_result,
        ),
        notes=notes,
    )
