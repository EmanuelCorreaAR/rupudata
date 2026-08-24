"""RupuData CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from rupudata.analyzers.near_duplicates import NearDuplicateConfig
from rupudata.comparison.diff import compare_datasets
from rupudata.contamination.check import check_benchmark
from rupudata.core.policy import (
    evaluate_benchmark_gate,
    evaluate_compare_gate,
    evaluate_scan_gate,
)
from rupudata.core.scanner import scan_dataset
from rupudata.reporters.json_report import write_json_report
from rupudata.reporters.terminal import (
    render_benchmark_terminal,
    render_compare_terminal,
    render_terminal,
)

# Exit codes: 0 ok, 1 I/O or usage error, 2 quality-policy failure (CI gate).
EXIT_ERROR = 1
EXIT_POLICY = 2
# Back-compat alias for tests / importers.
EXIT_OVERLAP = EXIT_POLICY

app = typer.Typer(
    name="rupudata",
    help=(
        "Local-first CLI for inspecting and auditing AI datasets.\n\n"
        "Policy gates (--fail-on-overlap, --max-*-rate) live on each command:\n"
        "  rupudata compare --help\n"
        "  rupudata benchmark-check --help\n"
        "  rupudata scan --help"
    ),
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console(stderr=True)


def _print_gate_failure(gate) -> None:
    failed = [r for r in gate.rules if not r.passed]
    details = ", ".join(
        f"{r.metric}={r.actual:.6g}>{r.threshold:.6g}" for r in failed
    )
    console.print(
        f"[red]Policy gate failed[/red] ({details}); "
        f"exiting {EXIT_POLICY}."
    )


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
    max_evidence: int = typer.Option(
        100,
        "--max-evidence",
        min=1,
        help="Max near-duplicate evidence pairs in the JSON report.",
    ),
    max_duplicate_rate: Optional[float] = typer.Option(
        None,
        "--max-duplicate-rate",
        min=0.0,
        max=1.0,
        help="Exit 2 if exact duplicate_rate exceeds this threshold (CI gate).",
    ),
    max_near_duplicate_rate: Optional[float] = typer.Option(
        None,
        "--max-near-duplicate-rate",
        min=0.0,
        max=1.0,
        help=(
            "Exit 2 if near-duplicate record_rate exceeds this threshold "
            "(CI gate; requires near-dupe analysis)."
        ),
    ),
) -> None:
    """Inspect a dataset: structure, fingerprint, exact and near duplicates."""
    config = NearDuplicateConfig(
        threshold=near_duplicate_threshold,
        shingle_size=shingle_size,
        num_perm=num_perm,
        enabled=not skip_near_duplicates,
        max_evidence=max_evidence,
    )
    try:
        report = scan_dataset(path, near_config=config)
        gate = evaluate_scan_gate(
            report,
            max_duplicate_rate=max_duplicate_rate,
            max_near_duplicate_rate=max_near_duplicate_rate,
        )
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=EXIT_ERROR) from exc

    if gate is not None:
        report = report.model_copy(
            update={
                "gate": gate,
                "configuration": report.configuration.model_copy(
                    update={
                        "max_duplicate_rate": max_duplicate_rate,
                        "max_near_duplicate_rate": max_near_duplicate_rate,
                    }
                ),
            }
        )

    report_path = output or Path("rupudata-report.json")
    written = write_json_report(report, report_path)
    render_terminal(report, str(written))

    if gate is not None and not gate.passed:
        _print_gate_failure(gate)
        raise typer.Exit(code=EXIT_POLICY)


@app.command(
    "compare",
    help=(
        "Compare two datasets for exact/normalized overlap "
        "(--text-field, --fail-on-overlap, --max-overlap-rate)."
    ),
)
def compare(
    path_a: Path = typer.Argument(..., help="First dataset (JSONL or Parquet)."),
    path_b: Path = typer.Argument(..., help="Second dataset (JSONL or Parquet)."),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path for the JSON report (default: ./rupudata-compare.json).",
    ),
    max_evidence: int = typer.Option(
        100,
        "--max-evidence",
        help="Max row-pair evidence entries per match mode (exact / normalized).",
        min=1,
    ),
    text_field: Optional[str] = typer.Option(
        None,
        "--text-field",
        help=(
            "Compare values of this column with text_exact_v1 / text_normalized_v1 "
            "(unit=field_text). Default: full-record matching."
        ),
    ),
    fail_on_overlap: bool = typer.Option(
        False,
        "--fail-on-overlap",
        help=(
            "Exit 2 if exact or normalized overlap rate > 0 "
            "(same as --max-overlap-rate 0). Report is still written."
        ),
    ),
    max_overlap_rate: Optional[float] = typer.Option(
        None,
        "--max-overlap-rate",
        min=0.0,
        max=1.0,
        help=(
            "Exit 2 if exact_overlap.rate or normalized_overlap.rate exceeds this "
            "threshold (CI gate). Report is still written."
        ),
    ),
) -> None:
    """Compare two datasets for exact and normalized record overlap."""
    try:
        report = compare_datasets(
            path_a, path_b, max_evidence=max_evidence, text_field=text_field
        )
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=EXIT_ERROR) from exc

    gate = evaluate_compare_gate(
        report,
        fail_on_overlap=fail_on_overlap,
        max_overlap_rate=max_overlap_rate,
    )
    if gate is not None:
        report = report.model_copy(
            update={
                "gate": gate,
                "configuration": report.configuration.model_copy(
                    update={
                        "fail_on_overlap": fail_on_overlap,
                        "max_overlap_rate": max_overlap_rate,
                    }
                ),
            }
        )

    report_path = output or Path("rupudata-compare.json")
    written = write_json_report(report, report_path)
    render_compare_terminal(report, str(written))

    if gate is not None and not gate.passed:
        _print_gate_failure(gate)
        raise typer.Exit(code=EXIT_POLICY)


@app.command(
    "benchmark-check",
    help=(
        "Check dataset vs benchmark text overlap "
        "(--reference, --fail-on-overlap, --max-overlap-rate)."
    ),
)
def benchmark_check(
    path: Path = typer.Argument(..., help="Path to a JSONL or Parquet training/eval dataset."),
    benchmark: str = typer.Option(
        ...,
        "--benchmark",
        "-b",
        help="Benchmark id (currently: gsm8k).",
    ),
    reference: Optional[Path] = typer.Option(
        None,
        "--reference",
        help="Optional path to a full benchmark JSONL/Parquet. Default: packaged sample.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path for the JSON report (default: ./rupudata-benchmark.json).",
    ),
    max_evidence: int = typer.Option(
        100,
        "--max-evidence",
        help="Max row-pair evidence entries per match mode (exact / normalized).",
        min=1,
    ),
    fail_on_overlap: bool = typer.Option(
        False,
        "--fail-on-overlap",
        help=(
            "Exit 2 if exact or normalized match rate > 0 "
            "(same as --max-overlap-rate 0). Report is still written."
        ),
    ),
    max_overlap_rate: Optional[float] = typer.Option(
        None,
        "--max-overlap-rate",
        min=0.0,
        max=1.0,
        help=(
            "Exit 2 if exact_rate or normalized_rate exceeds this threshold "
            "(CI gate). Report is still written."
        ),
    ),
) -> None:
    """Check text overlap between a dataset and a known benchmark reference."""
    try:
        report = check_benchmark(
            path, benchmark, reference=reference, max_evidence=max_evidence
        )
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=EXIT_ERROR) from exc

    gate = evaluate_benchmark_gate(
        report,
        fail_on_overlap=fail_on_overlap,
        max_overlap_rate=max_overlap_rate,
    )
    if gate is not None:
        report = report.model_copy(
            update={
                "gate": gate,
                "configuration": report.configuration.model_copy(
                    update={
                        "fail_on_overlap": fail_on_overlap,
                        "max_overlap_rate": max_overlap_rate,
                    }
                ),
            }
        )

    report_path = output or Path("rupudata-benchmark.json")
    written = write_json_report(report, report_path)
    render_benchmark_terminal(report, str(written))

    if gate is not None and not gate.passed:
        _print_gate_failure(gate)
        raise typer.Exit(code=EXIT_POLICY)


@app.callback()
def main() -> None:
    """RupuData — follow the path of your data."""


if __name__ == "__main__":
    app()
