"""Orchestrate benchmark overlap checks into a technical audit contract."""

from __future__ import annotations

from pathlib import Path

from rupudata import __version__
from rupudata.contamination.matcher import (
    DEFAULT_MAX_EVIDENCE,
    build_overlap_evidence,
    index_rows,
)
from rupudata.contamination.registry import get_adapter
from rupudata.core.models import (
    BenchmarkCheckReport,
    BenchmarkConfiguration,
    BenchmarkInput,
    BenchmarkMethod,
    BenchmarkResult,
    DatasetRef,
    MatchEvidence,
    MatchEvidenceItem,
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


def _to_items(pairs) -> list[MatchEvidenceItem]:
    return [
        MatchEvidenceItem(
            dataset_record=p.dataset_record,
            reference_record=p.reference_record,
            field=p.field,
        )
        for p in pairs
    ]


def check_benchmark(
    dataset_path: str | Path,
    benchmark_id: str,
    *,
    reference: str | Path | None = None,
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
) -> BenchmarkCheckReport:
    adapter = get_adapter(benchmark_id)
    data_path = Path(dataset_path).expanduser().resolve()
    df, fmt = read_dataset(data_path)

    ref_path = Path(reference) if reference is not None else None
    loaded = adapter.load_reference(ref_path)
    fields = adapter.comparable_fields()

    exact_ds = index_rows(df, normalized=False, fields=fields)
    exact_ref = index_rows(loaded.frame, normalized=False, fields=fields)
    norm_ds = index_rows(df, normalized=True, fields=fields)
    norm_ref = index_rows(loaded.frame, normalized=True, fields=fields)

    exact_ev = build_overlap_evidence(exact_ds, exact_ref, max_pairs=max_evidence)
    norm_ev = build_overlap_evidence(norm_ds, norm_ref, max_pairs=max_evidence)

    status = (
        "OVERLAP_DETECTED"
        if exact_ev.unique_texts or norm_ev.unique_texts
        else "NO_OVERLAP_DETECTED"
    )

    notes = [
        "This report is a technical audit contract (input → configuration → method → result).",
        "RupuData detected text overlap under the configured matching methodology — not a legal or scientific contamination verdict.",
        "Interpretation of whether overlap constitutes contamination depends on context.",
        "result.matches lists concrete row pairs (0-based) and the field used on the dataset side.",
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
            exact_matches=exact_ev.unique_texts,
            normalized_matches=norm_ev.unique_texts,
            near_matches=0,
            status=status,
            matches=MatchEvidence(
                exact=_to_items(exact_ev.pairs),
                normalized=_to_items(norm_ev.pairs),
                exact_truncated=exact_ev.truncated,
                normalized_truncated=norm_ev.truncated,
            ),
        ),
        notes=notes,
    )
