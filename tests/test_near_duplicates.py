"""Tests for near-duplicate detection."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from typer.testing import CliRunner

from rupudata.analyzers.near_duplicates import (
    NearDuplicateConfig,
    analyze_near_duplicates,
    char_shingles,
    jaccard,
    minhash_signature,
    record_text,
)
from rupudata.cli import app
from rupudata.core.scanner import scan_dataset

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
NEAR = EXAMPLES / "near_dupes.jsonl"
runner = CliRunner()


def test_jaccard_identical() -> None:
    s = char_shingles("hello world", 5)
    assert jaccard(s, s) == 1.0


def test_jaccard_known_similar_pair() -> None:
    a = char_shingles("The capital of France is Paris.", 5)
    b = char_shingles("The capital of France is Paris!", 5)
    assert jaccard(a, b) >= 0.85


def test_jaccard_dissimilar_pair() -> None:
    a = char_shingles("The capital of France is Paris.", 5)
    b = char_shingles("Completely unrelated content about alpine goats.", 5)
    assert jaccard(a, b) < 0.5


def test_minhash_deterministic() -> None:
    shingles = char_shingles("deterministic text for hashing", 5)
    a = minhash_signature(shingles, num_perm=32, seed=42)
    b = minhash_signature(shingles, num_perm=32, seed=42)
    assert a == b


def test_record_text_prefers_text_field() -> None:
    assert record_text({"text": "  hello  ", "source": "x"}) == "hello"


def test_analyze_near_dupes_fixture() -> None:
    df = pl.read_ndjson(NEAR)
    result = analyze_near_duplicates(
        df,
        NearDuplicateConfig(threshold=0.85, shingle_size=5),
    )
    assert result.enabled
    assert result.pairs >= 1
    assert result.records_flagged >= 2
    assert result.similarity == "character_shingles+jaccard"
    assert result.candidate_generation == "pairwise"
    assert result.minhash.enabled is False
    assert result.minhash.num_perm is None


def test_exact_duplicates_not_counted_as_near() -> None:
    df = pl.DataFrame({"text": ["same text", "same text", "different enough content here"]})
    result = analyze_near_duplicates(df, NearDuplicateConfig(threshold=0.85))
    assert result.pairs == 0


def test_large_dataset_uses_minhash_lsh_in_report() -> None:
    """Above PAIRWISE_LIMIT, report must show MinHash was actually used."""
    from rupudata.analyzers.near_duplicates import PAIRWISE_LIMIT

    n = PAIRWISE_LIMIT + 1
    texts = [f"unique sentence number {i} with enough characters" for i in range(n)]
    # Make one near-duplicate pair
    texts[0] = "The capital of France is Paris."
    texts[1] = "The capital of France is Paris!"
    df = pl.DataFrame({"text": texts})
    result = analyze_near_duplicates(
        df,
        NearDuplicateConfig(threshold=0.85, shingle_size=5, num_perm=64),
    )
    assert result.candidate_generation == "minhash_lsh"
    assert result.minhash.enabled is True
    assert result.minhash.num_perm == 64


def test_scan_includes_near_duplicates() -> None:
    report = scan_dataset(NEAR)
    assert report.near_duplicates.pairs >= 1
    assert report.version.startswith("0.")


def test_scan_skip_near_duplicates_cli(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    result = runner.invoke(
        app,
        ["scan", str(NEAR), "-o", str(out), "--skip-near-duplicates"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["near_duplicates"]["enabled"] is False
    assert payload["near_duplicates"]["candidate_generation"] == "disabled"
    assert payload["near_duplicates"]["minhash"]["enabled"] is False
    assert "Near duplicates" in result.output or "skipped" in result.output


def test_scan_near_threshold_cli(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    result = runner.invoke(
        app,
        [
            "scan",
            str(NEAR),
            "-o",
            str(out),
            "--near-duplicate-threshold",
            "0.85",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Near-dupe pairs" in result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["near_duplicates"]["threshold"] == 0.85
    assert payload["near_duplicates"]["candidate_generation"] == "pairwise"
    assert payload["near_duplicates"]["minhash"] == {"enabled": False, "num_perm": None}
