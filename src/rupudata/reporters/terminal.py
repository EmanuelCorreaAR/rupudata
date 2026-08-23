"""Terminal report via Rich."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rupudata.core.models import ScanReport


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


def render_terminal(report: ScanReport, output_path: str, console: Console | None = None) -> None:
    console = console or Console()
    console.print(
        Panel.fit(
            "[bold]RupuData[/bold] v" + report.version + "\n[dim]Follow the path of your data.[/dim]",
            border_style="cyan",
        )
    )
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
    dupes.add_row("Exact duplicates", f"{exact.duplicate_records:,}")
    dupes.add_row("Unique records", f"{exact.unique_records:,}")
    dupes.add_row("Duplicate rate", f"{exact.duplicate_rate * 100:.2f}%")
    console.print("[bold cyan]Duplicates[/bold cyan]")
    console.print("─" * 30)
    console.print(dupes)
    console.print()

    console.print(f"Report written to:\n[bold]{output_path}[/bold]\n")
    for note in report.notes:
        console.print(f"[dim]• {note}[/dim]")
