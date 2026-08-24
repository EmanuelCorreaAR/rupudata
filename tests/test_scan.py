"""Tests for fingerprinting and exact deduplication."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from rupudata.analyzers.duplicates import analyze_exact_duplicates
from rupudata.core.normalization import fingerprint_dataframe, hash_record
from rupudata.core.reader import detect_format, read_dataset
from rupudata.core.scanner import scan_dataset
from rupudata.reporters.json_report import write_json_report

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "example.jsonl"


def test_detect_format_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    assert detect_format(path).value == "jsonl"


def test_detect_format_parquet(tmp_path: Path) -> None:
    path = tmp_path / "data.parquet"
    pl.DataFrame({"a": [1]}).write_parquet(path)
    assert detect_format(path).value == "parquet"


def test_unsupported_format(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported"):
        detect_format(path)


def test_hash_record_normalizes_whitespace() -> None:
    a = hash_record({"text": "hello", "source": "x"})
    b = hash_record({"text": "  hello  ", "source": "x"})
    assert a == b


def test_fingerprint_order_independent() -> None:
    df_a = pl.DataFrame({"text": ["a", "b"], "n": [1, 2]})
    df_b = pl.DataFrame({"text": ["b", "a"], "n": [2, 1]})
    assert fingerprint_dataframe(df_a) == fingerprint_dataframe(df_b)


def test_fingerprint_changes_when_content_changes() -> None:
    df_a = pl.DataFrame({"text": ["a"]})
    df_b = pl.DataFrame({"text": ["b"]})
    assert fingerprint_dataframe(df_a) != fingerprint_dataframe(df_b)


def test_exact_duplicates_on_example() -> None:
    df, _ = read_dataset(EXAMPLES)
    result = analyze_exact_duplicates(df)
    assert result.total_records == 5
    assert result.unique_records == 3
    assert result.duplicate_records == 2


def test_scan_jsonl_writes_report(tmp_path: Path) -> None:
    report = scan_dataset(EXAMPLES)
    assert report.contract == "technical_audit"
    assert report.input.format == "jsonl"
    assert report.input.rows == 5
    assert report.result.fingerprint.startswith("rupu:")
    assert "text" in report.input.columns
    assert "source" in report.input.columns

    out = tmp_path / "report.json"
    write_json_report(report, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["tool"] == "rupudata"
    assert payload["contract"] == "technical_audit"
    assert "input" in payload
    assert "configuration" in payload
    assert "method" in payload
    assert "result" in payload
    assert payload["result"]["exact_duplicates"]["total_records"] == 5
    norm = payload["method"]["record_normalized"]
    assert norm["id"] == "record_normalized_v1"
    assert norm["string_strip"] is True
    assert norm["collapse_internal_whitespace"] is False
    assert norm["case_fold"] is False
    assert norm.get("unicode_normalize") is None
    assert payload["method"]["near_duplicates"]["text_prep"]["id"] == "near_text_v1"
    assert payload["configuration"]["row_index_base"] == 0
    assert payload["method"]["row_index_base"] == 0
    assert payload["method"]["fingerprint"] == "normalized_record_multiset_sha256"


def test_scan_parquet(tmp_path: Path) -> None:
    path = tmp_path / "sample.parquet"
    pl.DataFrame(
        {
            "text": ["same", "same", "other"],
            "source": ["a", "a", "b"],
        }
    ).write_parquet(path)

    report = scan_dataset(path)
    assert report.input.format == "parquet"
    assert report.input.rows == 3
    assert report.result.exact_duplicates.unique_records == 2
    assert report.result.exact_duplicates.duplicate_records == 1


def test_same_dataset_same_fingerprint(tmp_path: Path) -> None:
    a = scan_dataset(EXAMPLES)
    b = scan_dataset(EXAMPLES)
    assert a.result.fingerprint == b.result.fingerprint
