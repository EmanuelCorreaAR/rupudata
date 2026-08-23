"""Terminal report via Rich."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rupudata.core.models import CompareReport, ScanReport


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
    console.print("[bold cyan]Overlap[/bold cyan]")
    console.print("─" * 30)
    console.print(overlap)
    console.print()

    console.print(f"Report written to:\n[bold]{output_path}[/bold]\n")
    for note in report.notes:
        console.print(f"[dim]• {note}[/dim]")
