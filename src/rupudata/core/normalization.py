"""Record normalization and deterministic dataset fingerprinting."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import polars as pl


def canonicalize_value(value: Any) -> Any:
    """Normalize values so equivalent content hashes the same way."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return {k: canonicalize_value(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [canonicalize_value(v) for v in value]
    return str(value)


def record_canonical_bytes(record: dict[str, Any]) -> bytes:
    canonical = {k: canonicalize_value(record[k]) for k in sorted(record)}
    return json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def hash_record(record: dict[str, Any]) -> str:
    return hashlib.sha256(record_canonical_bytes(record)).hexdigest()


def fingerprint_dataframe(df: pl.DataFrame) -> str:
    """Compute a content fingerprint independent of row order.

    Method:
    1. Hash each normalized record (SHA-256).
    2. Sort the per-record hashes.
    3. Aggregate into a single SHA-256 digest.

    Same multiset of records → same fingerprint.
    Different content or counts → different fingerprint.
    """
    if df.height == 0:
        digest = hashlib.sha256(b"empty").hexdigest()
        return f"rupu:{digest[:16]}"

    hashes = sorted(hash_record(row) for row in df.iter_rows(named=True))
    aggregate = hashlib.sha256()
    for h in hashes:
        aggregate.update(h.encode("ascii"))
        aggregate.update(b"\n")

    return f"rupu:{aggregate.hexdigest()[:16]}"
