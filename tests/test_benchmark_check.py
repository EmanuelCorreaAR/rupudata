"""Tests for benchmark-check."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from rupudata.cli import app
from rupudata.contamination.adapters.base import BenchmarkAdapter
from rupudata.contamination.adapters.gsm8k import Gsm8kAdapter
from rupudata.contamination.check import check_benchmark
from rupudata.contamination.registry import get_adapter, list_adapters
from rupudata.core.models import BenchmarkMethod

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
TRAIN = EXAMPLES / "train_with_gsm8k_overlap.jsonl"
runner = CliRunner()


def test_gsm8k_is_registered_adapter() -> None:
    adapter = get_adapter("gsm8k")
    assert isinstance(adapter, Gsm8kAdapter)
    assert isinstance(adapter, BenchmarkAdapter)
    assert adapter.candidate_fields()[0] == "question"
    assert "comparable_fields" not in Gsm8kAdapter.__dict__
    assert any(a.id == "gsm8k" for a in list_adapters())


def test_gsm8k_sample_detects_exact_and_normalized_overlap() -> None:
    report = check_benchmark(TRAIN, "gsm8k")
    assert report.contract == "technical_audit"
    assert report.input.benchmark_id == "gsm8k"
    assert report.input.reference_source == "packaged_sample"
    assert report.result.exact_matches >= 1
    assert report.result.normalized_matches >= report.result.exact_matches
    assert report.result.status == "OVERLAP_DETECTED"
    assert report.configuration.match_near_duplicate is False
    assert report.method.text_extraction.strategy == "first_non_empty"
    assert report.method.text_extraction.candidate_fields[0] == "question"
    assert "comparable_fields" not in BenchmarkMethod.model_fields
    assert report.method.text_exact.id == "text_exact_v1"
    assert report.method.text_exact.base_normalization == "record_exact_v1"
    assert report.method.text_normalized.id == "text_normalized_v1"
    assert report.method.text_normalized.base_normalization == "record_normalized_v1"
    assert report.result.matches.exact
    assert report.result.matches.exact[0].field == "question"
    assert isinstance(report.result.matches.exact[0].dataset_record, int)
    assert report.result.matches.normalized
    fields_used = {m.field for m in report.result.matches.normalized}
    assert "question" in fields_used
    assert any("does not compare all fields" in n for n in report.notes)


def test_benchmark_check_cli(tmp_path: Path) -> None:
    out = tmp_path / "bench.json"
    result = runner.invoke(
        app,
        [
            "benchmark-check",
            str(TRAIN),
            "--benchmark",
            "gsm8k",
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "OVERLAP_DETECTED" in result.output
    assert "Exact matches" in result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["contract"] == "technical_audit"
    assert payload["result"]["status"] == "OVERLAP_DETECTED"
    te = payload["method"]["text_extraction"]
    assert te["strategy"] == "first_non_empty"
    assert te["candidate_fields"][0] == "question"
    assert te["unit"] == "one comparison text per record"
    assert "comparable_fields" not in payload["method"]
    assert payload["method"]["text_exact"]["id"] == "text_exact_v1"
    assert payload["method"]["text_exact"]["base_normalization"] == "record_exact_v1"
    assert payload["method"]["text_normalized"]["id"] == "text_normalized_v1"
    assert payload["method"]["text_normalized"]["base_normalization"] == "record_normalized_v1"
    assert "text_normalization" not in payload["method"]
    assert "record_exact" not in payload["method"]
    assert "record_normalization" not in payload["method"]
    assert payload["method"]["row_index_base"] == 0
    assert payload["configuration"]["row_index_base"] == 0
    assert payload["configuration"]["max_evidence_pairs"] == 100
    assert payload["method"]["fingerprint"] == "normalized_record_multiset_sha256"
    assert payload["result"]["matches"]["exact"]
    assert "field" in payload["result"]["matches"]["exact"][0]
    assert "dataset_record" in payload["result"]["matches"]["exact"][0]
    assert payload["configuration"]["match_near_duplicate"] is False
    assert "Evidence" in result.output


def test_unknown_benchmark() -> None:
    try:
        check_benchmark(TRAIN, "not-a-real-bench")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Unknown benchmark" in str(exc)


def test_user_reference_path(tmp_path: Path) -> None:
    ref = tmp_path / "ref.jsonl"
    ref.write_text(
        '{"question": "SHARED_NORMALIZED_QUESTION_BBB about lunar mining yields."}\n',
        encoding="utf-8",
    )
    report = check_benchmark(TRAIN, "gsm8k", reference=ref)
    assert report.input.reference_source == "user_reference"
    assert report.result.normalized_matches >= 1
