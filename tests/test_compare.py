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
    assert report.method.unit == "full_record"
    assert report.result.matches.exact
    assert report.result.matches.exact[0].dataset_a_record == 0
    assert report.result.matches.exact[0].dataset_b_record == 0
    assert len(report.result.matches.normalized) == 2

    by_rows = {
        (m.dataset_a_record, m.dataset_b_record): m
        for m in report.result.matches.normalized
    }
    assert by_rows[(0, 0)].also_exact is True
    assert by_rows[(0, 0)].differing_fields is None
    assert by_rows[(0, 0)].difference is None
    only_norm = by_rows[(2, 2)]
    assert only_norm.also_exact is False
    assert only_norm.differing_fields
    assert only_norm.differing_fields[0].field == "text"
    assert "shared after strip" in only_norm.differing_fields[0].a
    assert only_norm.differing_fields[0].b == "shared after strip"
    assert any("Exact evidence" in n for n in report.notes)


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
    assert "also_exact" not in payload["result"]["matches"]["exact"][0]
    assert "differing_fields" not in payload["result"]["matches"]["exact"][0]
    assert len(payload["result"]["matches"]["normalized"]) == 2
    also_exact_norm = next(
        m
        for m in payload["result"]["matches"]["normalized"]
        if m["also_exact"] is True
    )
    assert "differing_fields" not in also_exact_norm
    norm_only = next(
        m
        for m in payload["result"]["matches"]["normalized"]
        if m["also_exact"] is False
    )
    assert norm_only["differing_fields"][0]["field"] == "text"


def test_compare_text_field_differs_from_full_record_matching(tmp_path: Path) -> None:
    """Same text / different other fields: full-record miss, field_text hit."""
    path_a = tmp_path / "a.jsonl"
    path_b = tmp_path / "b.jsonl"
    path_a.write_text(
        '{"text": "hello world", "source": "train"}\n',
        encoding="utf-8",
    )
    path_b.write_text(
        '{"text": "hello world", "source": "evaluation"}\n',
        encoding="utf-8",
    )

    record_report = compare_datasets(path_a, path_b)
    text_report = compare_datasets(path_a, path_b, text_field="text")

    assert record_report.method.unit == "full_record"
    assert record_report.result.exact_overlap.shared_records == 0
    assert record_report.result.normalized_overlap.shared_records == 0

    assert text_report.method.unit == "field_text"
    assert text_report.method.field == "text"
    assert text_report.configuration.field == "text"
    assert text_report.result.exact_overlap.shared_records == 1
    assert text_report.result.normalized_overlap.shared_records == 1
    assert text_report.method.text_exact is not None
    assert text_report.method.text_normalized is not None
    assert text_report.method.record_exact is None
    assert text_report.result.matches.exact[0].field == "text"
    assert text_report.result.matches.normalized[0].also_exact is True


def test_compare_text_field_normalized_only_uses_difference(tmp_path: Path) -> None:
    path_a = tmp_path / "a.jsonl"
    path_b = tmp_path / "b.jsonl"
    path_a.write_text('{"text": "  hello world  ", "id": 1}\n', encoding="utf-8")
    path_b.write_text('{"text": "hello world", "id": 2}\n', encoding="utf-8")
    report = compare_datasets(path_a, path_b, text_field="text")
    assert report.result.exact_overlap.shared_records == 0
    assert report.result.normalized_overlap.shared_records == 1
    match = report.result.matches.normalized[0]
    assert match.also_exact is False
    assert match.field == "text"
    assert match.differing_fields is None
    assert match.difference is not None
    assert "hello world" in match.difference.a
    assert match.difference.b == "hello world"


def test_compare_text_field_cli(tmp_path: Path) -> None:
    path_a = tmp_path / "a.jsonl"
    path_b = tmp_path / "b.jsonl"
    path_a.write_text('{"text": "hello world", "source": "train"}\n', encoding="utf-8")
    path_b.write_text(
        '{"text": "hello world", "source": "evaluation"}\n',
        encoding="utf-8",
    )
    out = tmp_path / "compare.json"
    result = runner.invoke(
        app,
        [
            "compare",
            str(path_a),
            str(path_b),
            "--text-field",
            "text",
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["method"]["unit"] == "field_text"
    assert payload["method"]["field"] == "text"
    assert payload["configuration"]["field"] == "text"
    assert payload["method"]["text_exact"]["id"] == "text_exact_v1"
    assert "record_exact" not in payload["method"]
    assert "text_field" not in payload["method"]
    assert payload["result"]["exact_overlap"]["shared_records"] == 1


def test_compare_missing_text_field_errors(tmp_path: Path) -> None:
    path = tmp_path / "x.jsonl"
    path.write_text('{"text": "a"}\n', encoding="utf-8")
    try:
        compare_datasets(path, path, text_field="missing")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "missing" in str(exc)


def test_compare_max_evidence_truncates(tmp_path: Path) -> None:
    path = tmp_path / "many.jsonl"
    lines = [f'{{"text": "row-{i}", "id": {i}}}' for i in range(5)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = compare_datasets(path, path, max_evidence=2)
    assert report.result.exact_overlap.shared_records == 5
    assert len(report.result.matches.exact) == 2
    assert report.result.matches.exact_truncated is True
    assert report.configuration.max_evidence_pairs == 2
