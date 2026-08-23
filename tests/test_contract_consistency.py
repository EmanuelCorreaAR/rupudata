"""Cross-command technical audit contract consistency."""

from __future__ import annotations

from pathlib import Path

from rupudata.comparison.diff import compare_datasets
from rupudata.contamination.check import check_benchmark
from rupudata.core.models import (
    CONTRACT_ID,
    DISCLAIMER,
    FINGERPRINT_METHOD_ID,
    NOTE_CONTRACT,
    NOTE_EXACT_VOCABULARY,
    NOTE_NOT_CONTAMINATION,
    NOTE_ROW_INDICES,
    NOTE_TECHNICAL_SIGNALS,
    RECORD_EXACT_V1,
    RECORD_NORMALIZATION_V1,
    ROW_INDEX_BASE_DEFAULT,
    TEXT_EXACT_V1,
    TEXT_NORMALIZED_V1,
)
from rupudata.core.scanner import scan_dataset

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
CONTRACT_KEYS = ("tool", "version", "contract", "disclaimer", "input", "configuration", "method", "result", "notes")


def _assert_shared_shell(report) -> None:
    payload = report.to_dict()
    for key in CONTRACT_KEYS:
        assert key in payload, f"missing {key}"
    assert payload["tool"] == "rupudata"
    assert payload["contract"] == CONTRACT_ID
    assert payload["disclaimer"] == DISCLAIMER
    assert NOTE_CONTRACT in report.notes
    assert NOTE_TECHNICAL_SIGNALS in report.notes
    assert NOTE_NOT_CONTAMINATION in report.notes
    assert NOTE_ROW_INDICES in report.notes
    assert NOTE_EXACT_VOCABULARY in report.notes


def test_scan_compare_benchmark_share_contract_shell() -> None:
    scan = scan_dataset(EXAMPLES / "example.jsonl")
    compare = compare_datasets(EXAMPLES / "train.jsonl", EXAMPLES / "eval.jsonl")
    bench = check_benchmark(EXAMPLES / "train_with_gsm8k_overlap.jsonl", "gsm8k")

    for report in (scan, compare, bench):
        _assert_shared_shell(report)

    assert scan.method.fingerprint == FINGERPRINT_METHOD_ID
    assert compare.method.fingerprint == FINGERPRINT_METHOD_ID
    assert bench.method.fingerprint == FINGERPRINT_METHOD_ID

    assert scan.configuration.row_index_base == ROW_INDEX_BASE_DEFAULT
    assert compare.configuration.row_index_base == ROW_INDEX_BASE_DEFAULT
    assert bench.configuration.row_index_base == ROW_INDEX_BASE_DEFAULT
    assert scan.method.row_index_base == ROW_INDEX_BASE_DEFAULT
    assert compare.method.row_index_base == ROW_INDEX_BASE_DEFAULT
    assert bench.method.row_index_base == ROW_INDEX_BASE_DEFAULT

    assert scan.method.record_normalized.id == RECORD_NORMALIZATION_V1.id
    assert compare.method.record_normalized.id == RECORD_NORMALIZATION_V1.id
    assert compare.method.record_exact.id == RECORD_EXACT_V1.id
    assert bench.method.text_exact.id == TEXT_EXACT_V1.id
    assert bench.method.text_normalized.id == TEXT_NORMALIZED_V1.id
    assert bench.method.text_exact.base_normalization == "record_exact_v1"
    assert bench.method.text_normalized.base_normalization == "record_normalized_v1"
    assert "comparable_fields" not in bench.to_dict()["method"]

    assert compare.configuration.max_evidence_pairs == bench.configuration.max_evidence_pairs
    assert "NOT compare exact_overlap" in scan.method.exact_duplicates
    assert "record_exact_v1" in compare.method.exact_overlap
    assert "record_normalized_v1" in compare.method.normalized_overlap
    assert compare.method.unit == "full_record"
    assert "text_exact_v1" in bench.method.exact
    assert "text_normalized_v1" in bench.method.normalized
