"""GSM8K benchmark adapter."""

from __future__ import annotations

import io
from importlib import resources
from pathlib import Path

import polars as pl

from rupudata.contamination.adapters.base import ReferenceLoad
from rupudata.contamination.matcher import load_table


class Gsm8kAdapter:
    id = "gsm8k"
    name = "GSM8K"
    description = (
        "Grade School Math 8K style question text (sample reference for demos/CI)."
    )
    notes = (
        "The packaged file is a tiny SAMPLE for demos and tests, not the full GSM8K corpus.",
        "For real audits, pass --reference pointing at your GSM8K JSONL/Parquet export.",
        "Overlap is technical evidence under exact/normalized text matching — not a contamination verdict.",
    )
    packaged_sample = "gsm8k_sample.jsonl"

    def candidate_fields(self) -> list[str]:
        return ["question", "problem", "prompt", "text"]

    def comparable_fields(self) -> list[str]:
        """Deprecated alias of ``candidate_fields``."""
        return self.candidate_fields()

    def load_reference(self, reference: Path | None = None) -> ReferenceLoad:
        if reference is not None:
            path = Path(reference).expanduser().resolve()
            if not path.is_file():
                raise FileNotFoundError(f"Reference dataset not found: {path}")
            return ReferenceLoad(
                frame=load_table(path),
                source="user_reference",
                path=str(path),
            )

        payload = (
            resources.files("rupudata.data.benchmarks")
            .joinpath(self.packaged_sample)
            .read_text(encoding="utf-8")
        )
        return ReferenceLoad(
            frame=pl.read_ndjson(io.StringIO(payload)),
            source="packaged_sample",
            path=f"rupudata.data.benchmarks/{self.packaged_sample}",
        )
