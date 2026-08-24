"""Tests for --fail-on-overlap CI / pipeline exit codes."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from rupudata.cli import EXIT_ERROR, EXIT_OVERLAP, app

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
TRAIN = EXAMPLES / "train.jsonl"
EVAL = EXAMPLES / "eval.jsonl"
GSM8K_TRAIN = EXAMPLES / "train_with_gsm8k_overlap.jsonl"
runner = CliRunner()


def test_compare_fail_on_overlap_exits_2(tmp_path: Path) -> None:
    out = tmp_path / "compare.json"
    result = runner.invoke(
        app,
        [
            "compare",
            str(TRAIN),
            str(EVAL),
            "--fail-on-overlap",
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == EXIT_OVERLAP, result.output
    assert "Policy gate failed" in result.output or "Overlap detected" in result.output
    assert out.exists()


def test_compare_without_flag_exits_0_on_overlap(tmp_path: Path) -> None:
    out = tmp_path / "compare.json"
    result = runner.invoke(
        app,
        ["compare", str(TRAIN), str(EVAL), "-o", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_compare_fail_on_overlap_clean_exits_0(tmp_path: Path) -> None:
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text('{"text": "only in a"}\n', encoding="utf-8")
    b.write_text('{"text": "only in b"}\n', encoding="utf-8")
    out = tmp_path / "compare.json"
    result = runner.invoke(
        app,
        ["compare", str(a), str(b), "--fail-on-overlap", "-o", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_benchmark_fail_on_overlap_exits_2(tmp_path: Path) -> None:
    out = tmp_path / "bench.json"
    result = runner.invoke(
        app,
        [
            "benchmark-check",
            str(GSM8K_TRAIN),
            "--benchmark",
            "gsm8k",
            "--fail-on-overlap",
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == EXIT_OVERLAP, result.output
    assert "OVERLAP_DETECTED" in result.output
    assert "Policy gate failed" in result.output or "Overlap detected" in result.output
    assert out.exists()


def test_compare_missing_file_still_exits_1() -> None:
    result = runner.invoke(
        app,
        ["compare", "missing-a.jsonl", "missing-b.jsonl", "--fail-on-overlap"],
    )
    assert result.exit_code == EXIT_ERROR
