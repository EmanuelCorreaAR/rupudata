"""Registry of benchmark adapters."""

from __future__ import annotations

from rupudata.contamination.adapters.base import BenchmarkAdapter
from rupudata.contamination.adapters.gsm8k import Gsm8kAdapter

_ADAPTERS: dict[str, BenchmarkAdapter] = {
    Gsm8kAdapter.id: Gsm8kAdapter(),
}


def list_adapters() -> list[BenchmarkAdapter]:
    return sorted(_ADAPTERS.values(), key=lambda a: a.id)


def get_adapter(benchmark_id: str) -> BenchmarkAdapter:
    key = benchmark_id.strip().lower()
    if key not in _ADAPTERS:
        known = ", ".join(sorted(_ADAPTERS))
        raise ValueError(f"Unknown benchmark '{benchmark_id}'. Known: {known}")
    return _ADAPTERS[key]


# Backwards-compatible aliases used by older imports/tests naming.
def list_benchmarks() -> list[BenchmarkAdapter]:
    return list_adapters()


def get_benchmark(benchmark_id: str) -> BenchmarkAdapter:
    return get_adapter(benchmark_id)
