"""Orchestrate benchmark overlap checks into a technical audit contract."""

from __future__ import annotations

import io
from importlib import resources
from pathlib import Path

import polars as pl

from rupudata import __version__
from rupudata.contamination.matcher import (
    count_overlap,
    load_table,
    unique_text_hashes,
)
from rupudata.contamination.registry import get_benchmark, resolve_user_reference
from rupudata.core.models import (
    BenchmarkCheckReport,
    BenchmarkConfiguration,
    BenchmarkInput,
    BenchmarkMethod,
    BenchmarkResult,
    DatasetRef,
    RECORD_EXACT_V1,
    RECORD_NORMALIZATION_V1,
)
from rupudata.core.normalization import fingerprint_dataframe
from rupudata.core.reader import file_size_bytes, read_dataset


def _load_packaged_sample(filename: str) -> pl.DataFrame:
    payload = (
        resources.files("rupudata.data.benchmarks")
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )
    return pl.read_ndjson(io.StringIO(payload))


def _dataset_ref(path: Path, df: pl.DataFrame, fmt: str) -> DatasetRef:
    return DatasetRef(
        path=str(path),
        format=fmt,
        rows=df.height,
        size_bytes=file_size_bytes(path),
        columns=list(df.columns),
        fingerprint=fingerprint_dataframe(df),
    )


def check_benchmark(
    dataset_path: str | Path,
    benchmark_id: str,
    *,
    reference: str | Path | None = None,
) -> BenchmarkCheckReport:
    info = get_benchmark(benchmark_id)
    data_path = Path(dataset_path).expanduser().resolve()
    df, fmt = read_dataset(data_path)

    if reference is not None:
        ref_path = resolve_user_reference(reference)
        bench_df = load_table(ref_path)
        reference_source = "user_reference"
        reference_path = str(ref_path)
        bench_rows = bench_df.height
        ref_fingerprint = fingerprint_dataframe(bench_df)
    else:
        bench_df = _load_packaged_sample(info.packaged_sample)
        reference_source = "packaged_sample"
        reference_path = f"rupudata.data.benchmarks/{info.packaged_sample}"
        bench_rows = bench_df.height
        ref_fingerprint = fingerprint_dataframe(bench_df)

    exact_data = unique_text_hashes(df, normalized=False)
    exact_bench = unique_text_hashes(bench_df, normalized=False)
    norm_data = unique_text_hashes(df, normalized=True)
    norm_bench = unique_text_hashes(bench_df, normalized=True)

    exact_matches = count_overlap(exact_data, exact_bench)
    normalized_matches = count_overlap(norm_data, norm_bench)
    status = (
        "OVERLAP_DETECTED"
        if exact_matches or normalized_matches
        else "NO_OVERLAP_DETECTED"
    )

    notes = [
        "This report is a technical audit contract (input → configuration → method → result).",
        "RupuData detected text overlap under the configured matching methodology — not a legal or scientific contamination verdict.",
        "Interpretation of whether overlap constitutes contamination depends on context.",
        "Near-duplicate / paraphrase / translation matching is not included in this release.",
        *info.notes,
    ]

    return BenchmarkCheckReport(
        version=__version__,
        input=BenchmarkInput(
            dataset=_dataset_ref(data_path, df, fmt.value),
            benchmark_id=info.id,
            benchmark_name=info.name,
            reference_source=reference_source,
            reference_path=reference_path,
            benchmark_records=bench_rows,
            benchmark_fingerprint=ref_fingerprint,
        ),
        configuration=BenchmarkConfiguration(
            benchmark=info.id,
            match_exact=True,
            match_normalized=True,
            match_near_duplicate=False,
        ),
        method=BenchmarkMethod(
            comparable_fields=["question", "problem", "prompt", "text"],
            exact="hash of comparable text without strip (record_exact_v1 on {text})",
            normalized="hash of comparable text with strip (record_normalized_v1 on {text})",
            near_duplicate="disabled",
            record_exact=RECORD_EXACT_V1,
            record_normalization=RECORD_NORMALIZATION_V1,
        ),
        result=BenchmarkResult(
            exact_matches=exact_matches,
            normalized_matches=normalized_matches,
            near_matches=0,
            status=status,
        ),
        notes=notes,
    )
