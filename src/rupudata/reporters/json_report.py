"""Machine-readable JSON report writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol


class ReportLike(Protocol):
    def to_dict(self) -> dict: ...


def write_json_report(report: ReportLike, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path.resolve()
