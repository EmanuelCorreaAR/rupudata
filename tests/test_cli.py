"""CLI integration tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from rupudata.cli import app

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "example.jsonl"
runner = CliRunner()


def test_scan_command(tmp_path: Path) -> None:
    out = tmp_path / "audit.json"
    result = runner.invoke(app, ["scan", str(EXAMPLES), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert "RupuData" in result.output
    assert "Fingerprint" in result.output
    assert out.exists()
    assert "rupu:" in out.read_text(encoding="utf-8")


def test_scan_missing_file() -> None:
    result = runner.invoke(app, ["scan", "does-not-exist.jsonl"])
    assert result.exit_code == 1
    assert "Error" in result.output or "not found" in result.output.lower()
