"""Orchestrate benchmark overlap checks into a technical audit contract."""

from __future__ import annotations

from pathlib import Path

from rupudata import __version__
from rupudata.contamination.matcher import count_overlap, unique_text_hashes
from rupudata.contamination.registry import get_adapter
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


def _dataset_ref(path: Path, df, fmt: str) -> DatasetRef:
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
    adapter = get_adapter(benchmark_id)
    data_path = Path(dataset_path).expanduser().resolve()
    df, fmt = read_dataset(data_path)

    ref_path = Path(reference) if reference is not None else None
    loaded = adapter.load_reference(ref_path)
    fields = adapter.comparable_fields()

    exact_data = unique_text_hashes(df, normalized=False, fields=fields)
    exact_bench = unique_text_hashes(loaded.frame, normalized=False, fields=fields)
    norm_data = unique_text_hashes(df, normalized=True, fields=fields)
    norm_bench = unique_text_hashes(loaded.frame, normalized=True, fields=fields)

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
        *adapter.notes,
    ]

    return BenchmarkCheckReport(
        version=__version__,
        input=BenchmarkInput(
            dataset=_dataset_ref(data_path, df, fmt.value),
            benchmark_id=adapter.id,
            benchmark_name=adapter.name,
            reference_source=loaded.source,
            reference_path=loaded.path,
            benchmark_records=loaded.frame.height,
            benchmark_fingerprint=fingerprint_dataframe(loaded.frame),
        ),
        configuration=BenchmarkConfiguration(
            benchmark=adapter.id,
            match_exact=True,
            match_normalized=True,
            match_near_duplicate=False,
        ),
        method=BenchmarkMethod(
            comparable_fields=list(fields),
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
