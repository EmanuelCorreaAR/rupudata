"""RupuData CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from rupudata.analyzers.near_duplicates import NearDuplicateConfig
from rupudata.comparison.diff import compare_datasets
from rupudata.core.scanner import scan_dataset
from rupudata.reporters.json_report import write_json_report
from rupudata.reporters.terminal import render_compare_terminal, render_terminal

app = typer.Typer(
    name="rupudata",
    help="Local-first CLI for inspecting and auditing AI datasets.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console(stderr=True)


@app.command("scan")
def scan(
    path: Path = typer.Argument(..., help="Path to a JSONL or Parquet dataset."),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path for the JSON report (default: ./rupudata-report.json).",
    ),
    near_duplicate_threshold: float = typer.Option(
        0.85,
        "--near-duplicate-threshold",
        min=0.0,
        max=1.0,
        help="Jaccard threshold for near-duplicate pairs (character shingles).",
    ),
    shingle_size: int = typer.Option(
        5,
        "--shingle-size",
        min=1,
        help="Character shingle size for near-duplicate detection (unit is always character).",
    ),
    num_perm: int = typer.Option(
        64,
        "--num-perm",
        min=4,
        help="MinHash permutations (used when the dataset is large enough for LSH).",
    ),
    skip_near_duplicates: bool = typer.Option(
        False,
        "--skip-near-duplicates",
        help="Skip near-duplicate analysis (faster on large files).",
    ),
) -> None:
    """Inspect a dataset: structure, fingerprint, exact and near duplicates."""
    config = NearDuplicateConfig(
        threshold=near_duplicate_threshold,
        shingle_size=shingle_size,
        num_perm=num_perm,
        enabled=not skip_near_duplicates,
    )
    try:
        report = scan_dataset(path, near_config=config)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    report_path = output or Path("rupudata-report.json")
    written = write_json_report(report, report_path)
    render_terminal(report, str(written))


@app.command("compare")
def compare(
    path_a: Path = typer.Argument(..., help="First dataset (JSONL or Parquet)."),
    path_b: Path = typer.Argument(..., help="Second dataset (JSONL or Parquet)."),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path for the JSON report (default: ./rupudata-compare.json).",
    ),
) -> None:
    """Compare two datasets for exact and normalized record overlap."""
    try:
        report = compare_datasets(path_a, path_b)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    report_path = output or Path("rupudata-compare.json")
    written = write_json_report(report, report_path)
    render_compare_terminal(report, str(written))


@app.callback()
def main() -> None:
    """RupuData — follow the path of your data."""


if __name__ == "__main__":
    app()
