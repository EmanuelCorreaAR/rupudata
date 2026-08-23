"""Tests for benchmark-check."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from rupudata.cli import app
from rupudata.contamination.check import check_benchmark

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
TRAIN = EXAMPLES / "train_with_gsm8k_overlap.jsonl"
runner = CliRunner()


def test_gsm8k_sample_detects_exact_and_normalized_overlap() -> None:
    report = check_benchmark(TRAIN, "gsm8k")
    assert report.contract == "technical_audit"
    assert report.input.benchmark_id == "gsm8k"
    assert report.input.reference_source == "packaged_sample"
    assert report.result.exact_matches >= 1
    assert report.result.normalized_matches >= report.result.exact_matches
    assert report.result.status == "OVERLAP_DETECTED"
    assert report.configuration.match_near_duplicate is False


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
    assert payload["configuration"]["match_near_duplicate"] is False


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
