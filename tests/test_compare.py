"""Tests for dataset comparison."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from rupudata.cli import app
from rupudata.comparison.diff import compare_datasets
from rupudata.core.normalization import hash_record_exact, hash_record_normalized

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
TRAIN = EXAMPLES / "train.jsonl"
EVAL = EXAMPLES / "eval.jsonl"
runner = CliRunner()


def test_exact_vs_normalized_hash_differs_on_whitespace() -> None:
    padded = {"text": "  hello  ", "source": "x"}
    clean = {"text": "hello", "source": "x"}
    assert hash_record_exact(padded) != hash_record_exact(clean)
    assert hash_record_normalized(padded) == hash_record_normalized(clean)


def test_compare_train_eval_overlap() -> None:
    report = compare_datasets(TRAIN, EVAL)
    assert report.dataset_a.rows == 4
    assert report.dataset_b.rows == 4
    assert report.exact_overlap.shared_records == 1
    assert report.normalized_overlap.shared_records == 2
    assert report.exact_overlap.only_in_a == 3
    assert report.exact_overlap.only_in_b == 3
    assert report.dataset_a.fingerprint.startswith("rupu:")
    assert report.dataset_b.fingerprint.startswith("rupu:")
    assert report.dataset_a.fingerprint != report.dataset_b.fingerprint


def test_compare_identical_datasets(tmp_path: Path) -> None:
    path = tmp_path / "same.jsonl"
    path.write_text('{"text": "a"}\n{"text": "b"}\n', encoding="utf-8")
    report = compare_datasets(path, path)
    assert report.exact_overlap.shared_records == 2
    assert report.normalized_overlap.shared_records == 2
    assert report.exact_overlap.only_in_a == 0
    assert report.exact_overlap.only_in_b == 0
    assert report.dataset_a.fingerprint == report.dataset_b.fingerprint


def test_compare_cli(tmp_path: Path) -> None:
    out = tmp_path / "compare.json"
    result = runner.invoke(app, ["compare", str(TRAIN), str(EVAL), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert "Exact overlap" in result.output
    assert "Normalized overlap" in result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["exact_overlap"]["shared_records"] == 1
    assert payload["normalized_overlap"]["shared_records"] == 2
