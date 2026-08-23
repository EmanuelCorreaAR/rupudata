"""Orchestrate benchmark overlap checks into a technical audit contract."""

from __future__ import annotations

from pathlib import Path

from rupudata import __version__
from rupudata.contamination.matcher import (
    build_overlap_evidence,
    index_rows,
)
from rupudata.contamination.registry import get_adapter
from rupudata.core.models import (
    DEFAULT_MAX_EVIDENCE_PAIRS,
    FINGERPRINT_METHOD_ID,
    NOTE_CONTRACT,
    NOTE_EXACT_VOCABULARY,
    NOTE_NOT_CONTAMINATION,
    NOTE_ROW_INDICES,
    NOTE_TECHNICAL_SIGNALS,
    ROW_INDEX_BASE_DEFAULT,
    BenchmarkCheckReport,
    BenchmarkConfiguration,
    BenchmarkInput,
    BenchmarkMethod,
    BenchmarkResult,
    DatasetRef,
    MatchEvidence,
    MatchEvidenceItem,
    TEXT_EXACT_V1,
    TEXT_NORMALIZED_V1,
    TextExtractionSpec,
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
    max_evidence: int = DEFAULT_MAX_EVIDENCE_PAIRS,
) -> BenchmarkCheckReport:
    adapter = get_adapter(benchmark_id)
    data_path = Path(dataset_path).expanduser().resolve()
    df, fmt = read_dataset(data_path)

    ref_path = Path(reference) if reference is not None else None
    loaded = adapter.load_reference(ref_path)
    fields = list(adapter.candidate_fields())

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
        NOTE_CONTRACT,
        NOTE_TECHNICAL_SIGNALS,
        NOTE_NOT_CONTAMINATION,
        NOTE_ROW_INDICES,
        NOTE_EXACT_VOCABULARY,
        "RupuData selects one comparison text per record using the first non-empty candidate field. It does not compare all fields in a record.",
        "Pipeline: input → text extraction → exact/normalized matching → evidence → result.",
        "Interpretation of whether overlap constitutes contamination depends on context.",
        "result.matches lists concrete row pairs and the candidate field selected on the dataset side.",
        "Matching unit is extracted comparison text (text_exact_v1 / text_normalized_v1), not the full record.",
        "Near-duplicate / paraphrase / translation matching is not included in this release.",
        *adapter.notes,
    ]

    extraction = TextExtractionSpec(
        strategy="first_non_empty",
        candidate_fields=fields,
    )

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
            max_evidence_pairs=max_evidence,
            row_index_base=ROW_INDEX_BASE_DEFAULT,
        ),
        method=BenchmarkMethod(
            text_extraction=extraction,
            fingerprint=FINGERPRINT_METHOD_ID,
            row_index_base=ROW_INDEX_BASE_DEFAULT,
            exact="text_exact_v1 (extracted comparison text, no strip)",
            normalized="text_normalized_v1 (extracted comparison text, strip)",
            near_duplicate="disabled",
            text_exact=TEXT_EXACT_V1,
            text_normalized=TEXT_NORMALIZED_V1,
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
