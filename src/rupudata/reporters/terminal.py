"""Terminal report via Rich."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rupudata.core.models import CompareReport, ScanReport, BenchmarkCheckReport


def _format_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(n)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{n} B"


def _header(version: str, console: Console) -> None:
    console.print(
        Panel.fit(
            "[bold]RupuData[/bold] v" + version + "\n[dim]Follow the path of your data.[/dim]",
            border_style="cyan",
        )
    )


def render_terminal(report: ScanReport, output_path: str, console: Console | None = None) -> None:
    console = console or Console()
    _header(report.version, console)
    console.print(f"\nScanning: [bold]{report.input.path}[/bold]\n")

    dataset = Table(show_header=False, box=None, padding=(0, 2))
    dataset.add_column(style="bold")
    dataset.add_column()
    dataset.add_row("Rows", f"{report.input.rows:,}")
    dataset.add_row("Format", report.input.format)
    dataset.add_row("Size", _format_bytes(report.input.size_bytes))
    dataset.add_row("Columns", ", ".join(report.input.columns) or "(none)")
    dataset.add_row("Fingerprint", report.result.fingerprint)
    console.print("[bold cyan]Dataset[/bold cyan]")
    console.print("─" * 30)
    console.print(dataset)
    console.print()

    dupes = Table(show_header=False, box=None, padding=(0, 2))
    dupes.add_column(style="bold")
    dupes.add_column()
    exact = report.result.exact_duplicates
    near = report.result.near_duplicates
    cfg = report.configuration.near_duplicates
    dupes.add_row("Exact duplicates", f"{exact.duplicate_records:,}")
    dupes.add_row("Unique records", f"{exact.unique_records:,}")
    dupes.add_row("Duplicate rate", f"{exact.duplicate_rate * 100:.2f}%")
    if cfg.enabled:
        dupes.add_row("Near-dupe pairs", f"{near.pairs:,}")
        dupes.add_row("Records flagged", f"{near.records_flagged:,}")
        dupes.add_row("Near-dupe rate", f"{near.record_rate * 100:.2f}%")
        dupes.add_row("Near threshold", f"{cfg.threshold:.2f}")
        dupes.add_row("Candidates", report.method.near_duplicates.candidate_generation)
    else:
        dupes.add_row("Near duplicates", "skipped")
    console.print("[bold cyan]Duplicates[/bold cyan]")
    console.print("─" * 30)
    console.print(dupes)
    console.print()

    console.print(f"Report written to:\n[bold]{output_path}[/bold]\n")
    for note in report.notes:
        console.print(f"[dim]• {note}[/dim]")


def render_compare_terminal(
    report: CompareReport, output_path: str, console: Console | None = None
) -> None:
    console = console or Console()
    _header(report.version, console)
    console.print("\n[bold cyan]Dataset Diff[/bold cyan]\n")

    a = report.input.dataset_a
    b = report.input.dataset_b
    datasets = Table(show_header=True, box=None, padding=(0, 2))
    datasets.add_column("")
    datasets.add_column("A", style="bold")
    datasets.add_column("B", style="bold")
    datasets.add_row("Path", a.path, b.path)
    datasets.add_row("Rows", f"{a.rows:,}", f"{b.rows:,}")
    datasets.add_row("Format", a.format, b.format)
    datasets.add_row("Fingerprint", a.fingerprint, b.fingerprint)
    console.print(datasets)
    console.print()

    exact = report.result.exact_overlap
    normalized = report.result.normalized_overlap
    overlap = Table(show_header=False, box=None, padding=(0, 2))
    overlap.add_column(style="bold")
    overlap.add_column()
    overlap.add_row("Exact overlap", f"{exact.shared_records:,}")
    overlap.add_row("Normalized overlap", f"{normalized.shared_records:,}")
    overlap.add_row("Only in A (exact)", f"{exact.only_in_a:,}")
    overlap.add_row("Only in B (exact)", f"{exact.only_in_b:,}")
    overlap.add_row("Evidence pairs (exact)", f"{len(report.result.matches.exact):,}")
    overlap.add_row(
        "Evidence pairs (normalized)",
        f"{len(report.result.matches.normalized):,}",
    )
    console.print("[bold cyan]Overlap[/bold cyan]")
    console.print("─" * 30)
    console.print(overlap)
    console.print()

    evidence = report.result.matches.exact[:5] or report.result.matches.normalized[:5]
    if evidence:
        ev = Table(show_header=True, box=None, padding=(0, 2))
        ev.add_column("dataset_a_row")
        ev.add_column("dataset_b_row")
        for item in evidence:
            ev.add_row(str(item.dataset_a_record), str(item.dataset_b_record))
        console.print("[bold cyan]Evidence (sample)[/bold cyan]")
        console.print("─" * 30)
        console.print(ev)
        console.print()

    explained = [m for m in report.result.matches.normalized if m.also_exact is False][:3]
    if explained:
        diff_table = Table(show_header=True, box=None, padding=(0, 2))
        diff_table.add_column("a_row")
        diff_table.add_column("b_row")
        diff_table.add_column("field")
        diff_table.add_column("a")
        diff_table.add_column("b")
        for item in explained:
            for d in item.differing_fields[:3]:
                diff_table.add_row(
                    str(item.dataset_a_record),
                    str(item.dataset_b_record),
                    d.field,
                    d.a,
                    d.b,
                )
        console.print("[bold cyan]Normalized-only diffs (sample)[/bold cyan]")
        console.print("─" * 30)
        console.print(diff_table)
        console.print()

    console.print(f"Report written to:\n[bold]{output_path}[/bold]\n")
    for note in report.notes:
        console.print(f"[dim]• {note}[/dim]")


def render_benchmark_terminal(
    report: BenchmarkCheckReport, output_path: str, console: Console | None = None
) -> None:
    console = console or Console()
    _header(report.version, console)
    console.print(
        f"\nBenchmark check: [bold]{report.input.dataset.path}[/bold] "
        f"vs [bold]{report.input.benchmark_name}[/bold]\n"
    )

    meta = Table(show_header=False, box=None, padding=(0, 2))
    meta.add_column(style="bold")
    meta.add_column()
    meta.add_row("Benchmark", report.input.benchmark_name)
    meta.add_row("Reference", report.input.reference_source)
    meta.add_row("Benchmark records", f"{report.input.benchmark_records:,}")
    meta.add_row("Dataset rows", f"{report.input.dataset.rows:,}")
    meta.add_row("Benchmark fingerprint", report.input.benchmark_fingerprint)
    console.print("[bold cyan]Benchmark[/bold cyan]")
    console.print("─" * 30)
    console.print(meta)
    console.print()

    matches = Table(show_header=False, box=None, padding=(0, 2))
    matches.add_column(style="bold")
    matches.add_column()
    matches.add_row("Exact matches", f"{report.result.exact_matches:,}")
    matches.add_row("Normalized matches", f"{report.result.normalized_matches:,}")
    matches.add_row("Near matches", "n/a (disabled)")
    matches.add_row("Status", report.result.status)
    matches.add_row("Evidence pairs (exact)", f"{len(report.result.matches.exact):,}")
    matches.add_row(
        "Evidence pairs (normalized)",
        f"{len(report.result.matches.normalized):,}",
    )
    console.print("[bold cyan]Overlap[/bold cyan]")
    console.print("─" * 30)
    console.print(matches)
    console.print()

    evidence = report.result.matches.exact[:5] or report.result.matches.normalized[:5]
    if evidence:
        ev = Table(show_header=True, box=None, padding=(0, 2))
        ev.add_column("dataset_row")
        ev.add_column("reference_row")
        ev.add_column("field")
        for item in evidence:
            ev.add_row(
                str(item.dataset_record),
                str(item.reference_record),
                item.field,
            )
        console.print("[bold cyan]Evidence (sample)[/bold cyan]")
        console.print("─" * 30)
        console.print(ev)
        console.print()

    console.print(f"Report written to:\n[bold]{output_path}[/bold]\n")
    for note in report.notes:
        console.print(f"[dim]• {note}[/dim]")
