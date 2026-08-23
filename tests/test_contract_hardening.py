"""Contract hardening: matching-unit invariants (record_* vs text_*)."""

from __future__ import annotations

from pathlib import Path

from rupudata.contamination.check import check_benchmark
from rupudata.core.models import (
    BenchmarkMethod,
    CompareMethod,
    ScanMethod,
    TEXT_EXACT_V1,
    TEXT_NORMALIZED_V1,
    TextExactSpec,
)
from rupudata.core.normalization import hash_record_exact, hash_record_normalized
from rupudata.core.scanner import scan_dataset
from rupudata.comparison.diff import compare_datasets

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

PADDED = "  hello world  "
STRIPPED = "hello world"


def test_record_exact_differs_from_record_normalized_on_outer_whitespace() -> None:
    """record_exact_v1 ≠ record_normalized_v1 when only outer whitespace differs."""
    padded = {"text": PADDED, "source": "x"}
    stripped = {"text": STRIPPED, "source": "x"}

    assert hash_record_exact(padded) != hash_record_exact(stripped)
    assert hash_record_exact(padded) != hash_record_normalized(padded)
    assert hash_record_normalized(padded) == hash_record_normalized(stripped)
    assert hash_record_exact(stripped) == hash_record_normalized(stripped)


def test_text_exact_differs_from_text_normalized_on_outer_whitespace() -> None:
    """text_* reuse record string transforms on a plain {text} value."""
    padded = {"text": PADDED}
    stripped = {"text": STRIPPED}

    assert hash_record_exact(padded) != hash_record_exact(stripped)
    assert hash_record_normalized(padded) == hash_record_normalized(stripped)

    assert TEXT_EXACT_V1.base_normalization == "record_exact_v1"
    assert TEXT_NORMALIZED_V1.base_normalization == "record_normalized_v1"
    assert TEXT_EXACT_V1.string_strip is False
    assert TEXT_NORMALIZED_V1.string_strip is True
    assert "unit" not in TextExactSpec.model_fields


def test_benchmark_method_uses_text_specs_not_record_specs() -> None:
    report = check_benchmark(EXAMPLES / "train_with_gsm8k_overlap.jsonl", "gsm8k")
    method = report.to_dict()["method"]

    assert "text_extraction" in method
    assert "text_exact" in method
    assert "text_normalized" in method
    assert method["text_exact"]["id"] == "text_exact_v1"
    assert method["text_normalized"]["id"] == "text_normalized_v1"
    assert method["text_exact"]["base_normalization"] == "record_exact_v1"
    assert method["text_normalized"]["base_normalization"] == "record_normalized_v1"

    assert "record_exact" not in method
    assert "record_normalized" not in method
    assert "record_normalization" not in method
    assert "comparable_fields" not in method

    assert "record_exact" not in BenchmarkMethod.model_fields
    assert "record_normalized" not in BenchmarkMethod.model_fields
    assert "text_exact" in BenchmarkMethod.model_fields
    assert "text_normalized" in BenchmarkMethod.model_fields


def test_compare_and_scan_use_record_specs_not_text_specs() -> None:
    scan = scan_dataset(EXAMPLES / "example.jsonl").to_dict()["method"]
    compare = compare_datasets(
        EXAMPLES / "train.jsonl", EXAMPLES / "eval.jsonl"
    ).to_dict()["method"]

    assert "record_normalized" in scan
    assert "text_exact" not in scan
    assert "text_normalized" not in scan
    assert "text_extraction" not in scan

    assert compare["unit"] == "full_record"
    assert "record_exact" in compare
    assert "record_normalized" in compare
    assert "text_exact" not in compare
    assert "text_normalized" not in compare
    assert "text_extraction" not in compare

    assert "record_normalized" in ScanMethod.model_fields
    assert "text_exact" not in ScanMethod.model_fields
    assert "record_exact" in CompareMethod.model_fields
    assert "text_exact" in CompareMethod.model_fields


def test_compare_text_field_mode_emits_text_specs_not_record_specs() -> None:
    report = compare_datasets(
        EXAMPLES / "train.jsonl",
        EXAMPLES / "eval.jsonl",
        text_field="text",
    )
    method = report.to_dict()["method"]
    assert method["unit"] == "field_text"
    assert method["field"] == "text"
    assert "text_exact" in method
    assert "text_normalized" in method
    assert "record_exact" not in method
    assert "record_normalized" not in method
    assert "text_field" not in method


_EXACT_FORBIDDEN = frozenset({"also_exact", "differing_fields", "difference"})


def _assert_compare_match_evidence_shape(payload: dict, *, field_mode: bool) -> None:
    """JSON evidence: exact is lean; normalized always has also_exact; diffs only if needed."""
    matches = payload["result"]["matches"]
    for item in matches["exact"]:
        assert _EXACT_FORBIDDEN.isdisjoint(item), item
        assert "dataset_a_record" in item and "dataset_b_record" in item
        if field_mode:
            assert "field" in item
        else:
            assert "field" not in item

    for item in matches["normalized"]:
        assert "also_exact" in item
        assert "dataset_a_record" in item and "dataset_b_record" in item
        if field_mode:
            assert "field" in item
        if item["also_exact"] is True:
            assert "differing_fields" not in item
            assert "difference" not in item
        else:
            if field_mode:
                assert "difference" in item
                assert "differing_fields" not in item
            else:
                assert "differing_fields" in item
                assert item["differing_fields"]  # never empty when present
                assert "difference" not in item


def test_compare_full_record_match_evidence_omits_empty_diff_keys() -> None:
    payload = compare_datasets(
        EXAMPLES / "train.jsonl", EXAMPLES / "eval.jsonl"
    ).to_dict()
    _assert_compare_match_evidence_shape(payload, field_mode=False)
    assert any(m["also_exact"] is True for m in payload["result"]["matches"]["normalized"])
    assert any(m["also_exact"] is False for m in payload["result"]["matches"]["normalized"])


def test_compare_field_text_match_evidence_omits_empty_diff_keys(tmp_path: Path) -> None:
    path_a = tmp_path / "a.jsonl"
    path_b = tmp_path / "b.jsonl"
    path_a.write_text(
        '{"text": "same"}\n{"text": "  padded  "}\n',
        encoding="utf-8",
    )
    path_b.write_text(
        '{"text": "same"}\n{"text": "padded"}\n',
        encoding="utf-8",
    )
    payload = compare_datasets(path_a, path_b, text_field="text").to_dict()
    _assert_compare_match_evidence_shape(payload, field_mode=True)
    assert any(m["also_exact"] is True for m in payload["result"]["matches"]["normalized"])
    assert any(m["also_exact"] is False for m in payload["result"]["matches"]["normalized"])
