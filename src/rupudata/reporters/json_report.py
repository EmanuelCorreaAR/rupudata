"""Machine-readable JSON report writer."""

from __future__ import annotations

import json
from pathlib import Path

from rupudata.core.models import ScanReport


def write_json_report(report: ScanReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path.resolve()
