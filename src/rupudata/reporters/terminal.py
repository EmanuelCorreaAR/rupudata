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
    console.print(f"\nScanning: [bold]{report.dataset.path}[/bold]\n")

    dataset = Table(show_header=False, box=None, padding=(0, 2))
    dataset.add_column(style="bold")
    dataset.add_column()
    dataset.add_row("Rows", f"{report.dataset.rows:,}")
    dataset.add_row("Format", report.dataset.format)
    dataset.add_row("Size", _format_bytes(report.dataset.size_bytes))
    dataset.add_row("Columns", ", ".join(report.dataset.columns) or "(none)")
    dataset.add_row("Fingerprint", report.dataset.fingerprint)
    console.print("[bold cyan]Dataset[/bold cyan]")
    console.print("─" * 30)
    console.print(dataset)
    console.print()

    dupes = Table(show_header=False, box=None, padding=(0, 2))
    dupes.add_column(style="bold")
    dupes.add_column()
    exact = report.exact_duplicates
    near = report.near_duplicates
    dupes.add_row("Exact duplicates", f"{exact.duplicate_records:,}")
    dupes.add_row("Unique records", f"{exact.unique_records:,}")
    dupes.add_row("Duplicate rate", f"{exact.duplicate_rate * 100:.2f}%")
    if near.enabled:
        dupes.add_row("Near-dupe pairs", f"{near.pairs:,}")
        dupes.add_row("Records flagged", f"{near.records_flagged:,}")
        dupes.add_row("Near-dupe rate", f"{near.record_rate * 100:.2f}%")
        dupes.add_row("Near threshold", f"{near.threshold:.2f}")
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

    datasets = Table(show_header=True, box=None, padding=(0, 2))
    datasets.add_column("")
    datasets.add_column("A", style="bold")
    datasets.add_column("B", style="bold")
    datasets.add_row("Path", report.dataset_a.path, report.dataset_b.path)
    datasets.add_row("Rows", f"{report.dataset_a.rows:,}", f"{report.dataset_b.rows:,}")
    datasets.add_row("Format", report.dataset_a.format, report.dataset_b.format)
    datasets.add_row(
        "Fingerprint",
        report.dataset_a.fingerprint,
        report.dataset_b.fingerprint,
    )
    console.print(datasets)
    console.print()

    overlap = Table(show_header=False, box=None, padding=(0, 2))
    overlap.add_column(style="bold")
    overlap.add_column()
    overlap.add_row("Exact overlap", f"{report.exact_overlap.shared_records:,}")
    overlap.add_row("Normalized overlap", f"{report.normalized_overlap.shared_records:,}")
    overlap.add_row("Only in A (exact)", f"{report.exact_overlap.only_in_a:,}")
    overlap.add_row("Only in B (exact)", f"{report.exact_overlap.only_in_b:,}")
    console.print("[bold cyan]Overlap[/bold cyan]")
    console.print("─" * 30)
    console.print(overlap)
    console.print()

    console.print(f"Report written to:\n[bold]{output_path}[/bold]\n")
    for note in report.notes:
        console.print(f"[dim]• {note}[/dim]")
