"""Built-in benchmark adapters."""

from rupudata.contamination.adapters.base import BenchmarkAdapter, ReferenceLoad
from rupudata.contamination.adapters.gsm8k import Gsm8kAdapter

__all__ = ["BenchmarkAdapter", "Gsm8kAdapter", "ReferenceLoad"]
