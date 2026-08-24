"""Quality policy gates for CI / pipelines.

Rates and thresholds are technical policy signals, not legal judgments.
"""

from __future__ import annotations

from typing import Optional

from rupudata.core.models import (
    BenchmarkCheckReport,
    CompareReport,
    GateResult,
    GateRule,
    ScanReport,
)

# Metric ids (stable strings for JSON consumers)
METRIC_EXACT_OVERLAP_RATE = "exact_overlap_rate"
METRIC_NORMALIZED_OVERLAP_RATE = "normalized_overlap_rate"
METRIC_DUPLICATE_RATE = "duplicate_rate"
METRIC_NEAR_DUPLICATE_RATE = "near_duplicate_rate"
METRIC_EXACT_MATCH_RATE = "exact_match_rate"
METRIC_NORMALIZED_MATCH_RATE = "normalized_match_rate"

NOTE_OVERLAP_RATE = (
    "Overlap rate = shared_records / min(unique_a, unique_b), "
    "where unique_* = shared_records + only_in_*."
)
NOTE_MATCH_RATE = (
    "Match rate = matched_unique_texts / dataset_rows "
    "(fraction of dataset rows that share extracted text with the reference)."
)


def overlap_rate(shared: int, only_in_a: int, only_in_b: int) -> float:
    """Shared unique digests over the smaller unique-set size."""
    unique_a = shared + only_in_a
    unique_b = shared + only_in_b
    denom = min(unique_a, unique_b)
    if denom <= 0:
        return 0.0
    return shared / denom


def match_rate(matches: int, dataset_rows: int) -> float:
    if dataset_rows <= 0:
        return 0.0
    return matches / dataset_rows


def _rule(metric: str, threshold: float, actual: float) -> GateRule:
    # Pass when actual <= threshold (rates are upper bounds).
    return GateRule(
        metric=metric,
        threshold=threshold,
        actual=actual,
        passed=actual <= threshold,
    )


def _combine(rules: list[GateRule]) -> GateResult:
    return GateResult(passed=all(r.passed for r in rules), rules=rules)


def resolve_overlap_threshold(
    *,
    fail_on_overlap: bool,
    max_overlap_rate: Optional[float],
) -> Optional[float]:
    """Return the effective max overlap rate, or None if no overlap gate."""
    threshold: Optional[float] = None
    if fail_on_overlap:
        threshold = 0.0
    if max_overlap_rate is not None:
        threshold = (
            max_overlap_rate
            if threshold is None
            else min(threshold, max_overlap_rate)
        )
    return threshold


def evaluate_compare_gate(
    report: CompareReport,
    *,
    fail_on_overlap: bool = False,
    max_overlap_rate: Optional[float] = None,
) -> Optional[GateResult]:
    threshold = resolve_overlap_threshold(
        fail_on_overlap=fail_on_overlap,
        max_overlap_rate=max_overlap_rate,
    )
    if threshold is None:
        return None
    exact = report.result.exact_overlap
    normalized = report.result.normalized_overlap
    return _combine(
        [
            _rule(METRIC_EXACT_OVERLAP_RATE, threshold, exact.rate),
            _rule(METRIC_NORMALIZED_OVERLAP_RATE, threshold, normalized.rate),
        ]
    )


def evaluate_benchmark_gate(
    report: BenchmarkCheckReport,
    *,
    fail_on_overlap: bool = False,
    max_overlap_rate: Optional[float] = None,
) -> Optional[GateResult]:
    threshold = resolve_overlap_threshold(
        fail_on_overlap=fail_on_overlap,
        max_overlap_rate=max_overlap_rate,
    )
    if threshold is None:
        return None
    result = report.result
    return _combine(
        [
            _rule(METRIC_EXACT_MATCH_RATE, threshold, result.exact_rate),
            _rule(METRIC_NORMALIZED_MATCH_RATE, threshold, result.normalized_rate),
        ]
    )


def evaluate_scan_gate(
    report: ScanReport,
    *,
    max_duplicate_rate: Optional[float] = None,
    max_near_duplicate_rate: Optional[float] = None,
) -> Optional[GateResult]:
    rules: list[GateRule] = []
    if max_duplicate_rate is not None:
        rules.append(
            _rule(
                METRIC_DUPLICATE_RATE,
                max_duplicate_rate,
                report.result.exact_duplicates.duplicate_rate,
            )
        )
    if max_near_duplicate_rate is not None:
        if not report.configuration.near_duplicates.enabled:
            raise ValueError(
                "--max-near-duplicate-rate requires near-duplicate analysis "
                "(omit --skip-near-duplicates)."
            )
        rules.append(
            _rule(
                METRIC_NEAR_DUPLICATE_RATE,
                max_near_duplicate_rate,
                report.result.near_duplicates.record_rate,
            )
        )
    if not rules:
        return None
    return _combine(rules)
