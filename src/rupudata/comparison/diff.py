"""Compare two datasets for exact and normalized record overlap."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from rupudata import __version__
from rupudata.core.models import (
    CompareConfiguration,
    CompareInput,
    CompareMatchEvidence,
    CompareMatchItem,
    CompareMethod,
    CompareReport,
    CompareResult,
    DatasetRef,
    OverlapStats,
    RECORD_EXACT_V1,
    RECORD_NORMALIZATION_V1,
)
from rupudata.core.normalization import (
    fingerprint_dataframe,
    hash_record_exact,
    hash_record_normalized,
)
from rupudata.core.reader import file_size_bytes, read_dataset

DEFAULT_MAX_EVIDENCE = 100


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


def _build_record_overlap(
    hits_a: list[RecordHit],
    hits_b: list[RecordHit],
    *,
    max_pairs: int,
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


def _dataset_ref(path: Path, df: pl.DataFrame, fmt: str) -> DatasetRef:
    return DatasetRef(
        path=str(path),
        format=fmt,
        rows=df.height,
        size_bytes=file_size_bytes(path),
        columns=list(df.columns),
        fingerprint=fingerprint_dataframe(df),
    )


def compare_datasets(
    path_a: str | Path,
    path_b: str | Path,
    *,
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
) -> CompareReport:
    """Compare two local datasets by full-record hash overlap.

    Exact overlap uses stable serialization without string stripping.
    Normalized overlap applies light normalization (e.g. strip) first.

    This reports technical overlap under those methods — not semantic
    contamination, paraphrases, or translations. Matching is at full-record
    granularity (all fields), not text extraction.
    """
    a_path = Path(path_a).expanduser().resolve()
    b_path = Path(path_b).expanduser().resolve()

    df_a, fmt_a = read_dataset(a_path)
    df_b, fmt_b = read_dataset(b_path)

    exact_a = _index_records(df_a, hash_record_exact)
    exact_b = _index_records(df_b, hash_record_exact)
    norm_a = _index_records(df_a, hash_record_normalized)
    norm_b = _index_records(df_b, hash_record_normalized)

    exact_ev = _build_record_overlap(exact_a, exact_b, max_pairs=max_evidence)
    norm_ev = _build_record_overlap(norm_a, norm_b, max_pairs=max_evidence)

    ref_a = _dataset_ref(a_path, df_a, fmt_a.value)
    ref_b = _dataset_ref(b_path, df_b, fmt_b.value)

    return CompareReport(
        version=__version__,
        input=CompareInput(dataset_a=ref_a, dataset_b=ref_b),
        configuration=CompareConfiguration(
            match_exact=True,
            match_normalized=True,
            max_evidence_pairs=max_evidence,
            row_index_base=0,
        ),
        method=CompareMethod(
            record_exact=RECORD_EXACT_V1,
            record_normalization=RECORD_NORMALIZATION_V1,
        ),
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
                normalized=norm_ev.pairs,
                exact_truncated=exact_ev.truncated,
                normalized_truncated=norm_ev.truncated,
            ),
        ),
        notes=[
            "This report is a technical audit contract (input → configuration → method → result).",
            "Pipeline: input → full-record hashing → exact/normalized matching → evidence → result.",
            "Overlap counts unique full records shared by both datasets under each hashing method.",
            "result.matches lists concrete row pairs (0-based) under full-record matching — not text extraction.",
            "Normalized overlap strips leading/trailing whitespace in strings; exact does not.",
            "This is technical overlap evidence, not a claim of benchmark contamination.",
            "Paraphrases, translations, and semantic near-matches are not detected.",
        ],
    )
