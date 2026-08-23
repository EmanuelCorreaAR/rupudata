"""Record normalization and deterministic dataset fingerprinting.

Record normalization policy (``record_normalized_v1``), used by fingerprint and
exact duplicates in ``scan`` / normalized overlap in ``compare``:

- Include **all** fields of the record.
- Sort object keys recursively for stable JSON.
- Strings: ``str.strip()`` only (leading/trailing whitespace).
- Do **not** collapse internal whitespace, lowercase, or Unicode-normalize.
- Serialize as compact UTF-8 JSON with sorted keys; hash with SHA-256.

Example: ``\" Hello   World \"`` → ``\"Hello   World\"`` (internal spaces kept).

Fingerprint: SHA-256 over the sorted multiset of per-record normalized hashes,
then ``rupu:`` + first 16 hex chars.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import polars as pl


def _stable_value(value: Any) -> Any:
    """Sort keys recursively without changing string content."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return {k: _stable_value(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_stable_value(v) for v in value]
    return str(value)


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


def _dump_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def record_exact_bytes(record: dict[str, Any]) -> bytes:
    """Stable serialization without string stripping."""
    return _dump_bytes({k: _stable_value(record[k]) for k in sorted(record)})


def record_canonical_bytes(record: dict[str, Any]) -> bytes:
    """Stable serialization after light normalization (e.g. strip)."""
    return _dump_bytes({k: canonicalize_value(record[k]) for k in sorted(record)})


def hash_record_exact(record: dict[str, Any]) -> str:
    return hashlib.sha256(record_exact_bytes(record)).hexdigest()


def hash_record(record: dict[str, Any]) -> str:
    """Normalized record hash (used by scan/fingerprint)."""
    return hashlib.sha256(record_canonical_bytes(record)).hexdigest()


hash_record_normalized = hash_record

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
