"""Built-in benchmark reference registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkInfo:
    id: str
    name: str
    description: str
    packaged_sample: str
    notes: tuple[str, ...]


GSM8K = BenchmarkInfo(
    id="gsm8k",
    name="GSM8K",
    description="Grade School Math 8K style question text (sample reference for demos/CI).",
    packaged_sample="gsm8k_sample.jsonl",
    notes=(
        "The packaged file is a tiny SAMPLE for demos and tests, not the full GSM8K corpus.",
        "For real audits, pass --reference pointing at your GSM8K JSONL/Parquet export.",
        "Overlap is technical evidence under exact/normalized text matching — not a contamination verdict.",
    ),
)

REGISTRY: dict[str, BenchmarkInfo] = {
    GSM8K.id: GSM8K,
}


def list_benchmarks() -> list[BenchmarkInfo]:
    return sorted(REGISTRY.values(), key=lambda b: b.id)


def get_benchmark(benchmark_id: str) -> BenchmarkInfo:
    key = benchmark_id.strip().lower()
    if key not in REGISTRY:
        known = ", ".join(sorted(REGISTRY))
        raise ValueError(f"Unknown benchmark '{benchmark_id}'. Known: {known}")
    return REGISTRY[key]


def resolve_user_reference(reference: str | Path) -> Path:
    path = Path(reference).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Reference dataset not found: {path}")
    return path
