"""Tests for rates and quality-policy gates (0.9)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from rupudata.cli import EXIT_ERROR, EXIT_POLICY, app
from rupudata.comparison.diff import compare_datasets
from rupudata.core.policy import overlap_rate
from rupudata.core.scanner import scan_dataset

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
TRAIN = EXAMPLES / "train.jsonl"
EVAL = EXAMPLES / "eval.jsonl"
NEAR = EXAMPLES / "near_dupes.jsonl"
GSM8K_TRAIN = EXAMPLES / "train_with_gsm8k_overlap.jsonl"
runner = CliRunner()


def test_overlap_rate_formula() -> None:
    # shared=1, only_a=3, only_b=3 → unique 4 and 4 → rate 0.25
    assert overlap_rate(1, 3, 3) == 0.25
    assert overlap_rate(0, 5, 5) == 0.0


def test_compare_includes_overlap_rates() -> None:
    report = compare_datasets(TRAIN, EVAL)
    exact = report.result.exact_overlap
    assert exact.shared_records == 1
    assert exact.rate == overlap_rate(exact.shared_records, exact.only_in_a, exact.only_in_b)
    assert report.result.normalized_overlap.rate >= exact.rate
    assert report.gate is None


def test_compare_max_overlap_rate_fails(tmp_path: Path) -> None:
    out = tmp_path / "c.json"
    result = runner.invoke(
        app,
        [
            "compare",
            str(TRAIN),
            str(EVAL),
            "--max-overlap-rate",
            "0.001",
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == EXIT_POLICY, result.output
    assert "Policy gate failed" in result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["gate"]["passed"] is False
    metrics = {r["metric"] for r in payload["gate"]["rules"]}
    assert "exact_overlap_rate" in metrics
    assert "normalized_overlap_rate" in metrics


def test_compare_max_overlap_rate_passes_when_loose(tmp_path: Path) -> None:
    out = tmp_path / "c.json"
    result = runner.invoke(
        app,
        [
            "compare",
            str(TRAIN),
            str(EVAL),
            "--max-overlap-rate",
            "1.0",
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["gate"]["passed"] is True


def test_compare_fail_on_overlap_still_exits_2(tmp_path: Path) -> None:
    out = tmp_path / "c.json"
    result = runner.invoke(
        app,
        ["compare", str(TRAIN), str(EVAL), "--fail-on-overlap", "-o", str(out)],
    )
    assert result.exit_code == EXIT_POLICY, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["gate"]["passed"] is False
    assert all(r["threshold"] == 0.0 for r in payload["gate"]["rules"])


def test_scan_max_duplicate_rate(tmp_path: Path) -> None:
    out = tmp_path / "s.json"
    # example.jsonl has duplicates → rate > 0
    result = runner.invoke(
        app,
        [
            "scan",
            str(EXAMPLES / "example.jsonl"),
            "--skip-near-duplicates",
            "--max-duplicate-rate",
            "0",
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == EXIT_POLICY, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["gate"]["passed"] is False
    assert payload["gate"]["rules"][0]["metric"] == "duplicate_rate"


def test_scan_max_near_duplicate_rate(tmp_path: Path) -> None:
    out = tmp_path / "s.json"
    result = runner.invoke(
        app,
        [
            "scan",
            str(NEAR),
            "--max-near-duplicate-rate",
            "0",
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == EXIT_POLICY, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert any(r["metric"] == "near_duplicate_rate" for r in payload["gate"]["rules"])


def test_scan_max_near_requires_analysis(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "scan",
            str(NEAR),
            "--skip-near-duplicates",
            "--max-near-duplicate-rate",
            "0.01",
            "-o",
            str(tmp_path / "s.json"),
        ],
    )
    assert result.exit_code == EXIT_ERROR
    assert "near-duplicate" in result.output.lower()


def test_benchmark_max_overlap_rate(tmp_path: Path) -> None:
    out = tmp_path / "b.json"
    result = runner.invoke(
        app,
        [
            "benchmark-check",
            str(GSM8K_TRAIN),
            "--benchmark",
            "gsm8k",
            "--max-overlap-rate",
            "0",
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == EXIT_POLICY, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "exact_rate" in payload["result"]
    assert payload["gate"]["passed"] is False


def test_scan_without_gate_omits_gate_key() -> None:
    report = scan_dataset(EXAMPLES / "example.jsonl")
    assert report.gate is None
    assert "gate" not in report.to_dict()
