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
    assert report.contract == "technical_audit"
    assert report.input.dataset_a.rows == 4
    assert report.input.dataset_b.rows == 4
    assert report.result.exact_overlap.shared_records == 1
    assert report.result.normalized_overlap.shared_records == 2
    assert report.result.exact_overlap.only_in_a == 3
    assert report.result.exact_overlap.only_in_b == 3
    assert report.input.dataset_a.fingerprint.startswith("rupu:")
    assert report.input.dataset_b.fingerprint.startswith("rupu:")
    assert report.input.dataset_a.fingerprint != report.input.dataset_b.fingerprint
    assert report.configuration.match_exact is True
    assert report.method.unit.startswith("full record")
    assert report.result.matches.exact
    assert report.result.matches.exact[0].dataset_a_record == 0
    assert report.result.matches.exact[0].dataset_b_record == 0
    assert len(report.result.matches.normalized) == 2

    by_rows = {
        (m.dataset_a_record, m.dataset_b_record): m
        for m in report.result.matches.normalized
    }
    assert by_rows[(0, 0)].also_exact is True
    assert by_rows[(0, 0)].differing_fields == []
    only_norm = by_rows[(2, 2)]
    assert only_norm.also_exact is False
    assert only_norm.differing_fields
    assert only_norm.differing_fields[0].field == "text"
    assert "shared after strip" in only_norm.differing_fields[0].a
    assert only_norm.differing_fields[0].b == "shared after strip"
    assert any("differing_fields" in n for n in report.notes)


def test_compare_identical_datasets(tmp_path: Path) -> None:
    path = tmp_path / "same.jsonl"
    path.write_text('{"text": "a"}\n{"text": "b"}\n', encoding="utf-8")
    report = compare_datasets(path, path)
    assert report.result.exact_overlap.shared_records == 2
    assert report.result.normalized_overlap.shared_records == 2
    assert report.result.exact_overlap.only_in_a == 0
    assert report.result.exact_overlap.only_in_b == 0
    assert report.input.dataset_a.fingerprint == report.input.dataset_b.fingerprint
    assert {(m.dataset_a_record, m.dataset_b_record) for m in report.result.matches.exact} == {
        (0, 0),
        (1, 1),
    }
    assert all(m.also_exact is True for m in report.result.matches.normalized)


def test_compare_cli(tmp_path: Path) -> None:
    out = tmp_path / "compare.json"
    result = runner.invoke(
        app,
        ["compare", str(TRAIN), str(EVAL), "-o", str(out), "--max-evidence", "50"],
    )
    assert result.exit_code == 0, result.output
    assert "Exact overlap" in result.output
    assert "Normalized overlap" in result.output
    assert "Evidence" in result.output
    assert "Normalized-only diffs" in result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["contract"] == "technical_audit"
    assert payload["result"]["exact_overlap"]["shared_records"] == 1
    assert payload["result"]["normalized_overlap"]["shared_records"] == 2
    assert "method" in payload
    assert payload["method"]["record_exact"]["string_strip"] is False
    assert payload["method"]["record_normalized"]["string_strip"] is True
    assert "record_normalization" not in payload["method"]
    assert "field_diff" in payload["method"]
    assert payload["configuration"]["row_index_base"] == 0
    assert payload["configuration"]["max_evidence_pairs"] == 50
    assert payload["method"]["fingerprint"] == "normalized_record_multiset_sha256"
    assert payload["result"]["matches"]["exact"][0]["dataset_a_record"] == 0
    assert payload["result"]["matches"]["exact"][0]["dataset_b_record"] == 0
    assert len(payload["result"]["matches"]["normalized"]) == 2
    norm_only = next(
        m
        for m in payload["result"]["matches"]["normalized"]
        if m["also_exact"] is False
    )
    assert norm_only["differing_fields"][0]["field"] == "text"


def test_compare_max_evidence_truncates(tmp_path: Path) -> None:
    path = tmp_path / "many.jsonl"
    lines = [f'{{"text": "row-{i}", "id": {i}}}' for i in range(5)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = compare_datasets(path, path, max_evidence=2)
    assert report.result.exact_overlap.shared_records == 5
    assert len(report.result.matches.exact) == 2
    assert report.result.matches.exact_truncated is True
    assert report.configuration.max_evidence_pairs == 2
