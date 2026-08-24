"""Near-duplicate detection via character shingles, MinHash/LSH, and Jaccard.

Methodology (v0.3):
- Compare record *text* (prefer a ``text`` column; otherwise join string fields).
- Build character shingles of size ``shingle_size``.
- Generate MinHash signatures (deterministic seeded permutations) and LSH bands
  for candidate pairs when the unique-text count is large; otherwise compare
  all pairs directly.
- Verify candidates with true Jaccard similarity on shingle sets.
- Pairs with Jaccard >= threshold that are not exact normalized-record matches
  count as near-duplicates.

This approximates lexical similarity. It does not detect paraphrases,
translations, or semantic equivalence.
"""

from __future__ import annotations

import hashlib
import struct
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

import polars as pl

from rupudata.core.models import (
    DEFAULT_MAX_EVIDENCE_PAIRS,
    MinHashInfo,
    NearDuplicateEvidenceItem,
    NearDuplicateMethod,
    NearDuplicateResult,
)
from rupudata.core.normalization import hash_record

PAIRWISE_LIMIT = 250


@dataclass(frozen=True)
class NearDuplicateConfig:
    threshold: float = 0.85
    shingle_size: int = 5
    num_perm: int = 64
    seed: int = 42
    enabled: bool = True
    max_evidence: int = DEFAULT_MAX_EVIDENCE_PAIRS


@dataclass(frozen=True)
class NearDuplicateAnalysis:
    """Method actually executed + numeric result for the audit contract."""

    method: NearDuplicateMethod
    result: NearDuplicateResult


def record_text_and_field(record: dict[str, Any]) -> tuple[str, str | None]:
    """Extract comparable text and the field name used (when a single field)."""
    if "text" in record and record["text"] is not None:
        return str(record["text"]).strip(), "text"
    string_keys = [key for key, value in record.items() if isinstance(value, str)]
    if len(string_keys) == 1:
        key = string_keys[0]
        return str(record[key]).strip(), key
    if string_keys:
        parts = [str(record[key]).strip() for key in sorted(string_keys)]
        return " ".join(parts), None
    return "", None


def record_text(record: dict[str, Any]) -> str:
    """Extract comparable text from a record."""
    text, _ = record_text_and_field(record)
    return text


def char_shingles(text: str, size: int) -> set[str]:
    if size < 1:
        raise ValueError("shingle_size must be >= 1")
    normalized = " ".join(text.lower().split())
    if not normalized:
        return set()
    if len(normalized) < size:
        return {normalized}
    return {normalized[i : i + size] for i in range(len(normalized) - size + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def _stable_u32(payload: bytes) -> int:
    digest = hashlib.sha256(payload).digest()
    return struct.unpack(">I", digest[:4])[0]


def _permutation_params(num_perm: int, seed: int) -> list[tuple[int, int]]:
    """Deterministic (a, b) pairs for MinHash permutations over 32-bit space."""
    params: list[tuple[int, int]] = []
    for i in range(num_perm):
        a = _stable_u32(f"rupu-mh-a:{seed}:{i}".encode("utf-8")) | 1
        b = _stable_u32(f"rupu-mh-b:{seed}:{i}".encode("utf-8"))
        params.append((a, b))
    return params


def minhash_signature(shingles: set[str], num_perm: int, seed: int) -> tuple[int, ...]:
    if not shingles:
        return tuple(0 for _ in range(num_perm))
    params = _permutation_params(num_perm, seed)
    shingle_ids = [_stable_u32(s.encode("utf-8")) for s in shingles]
    signature: list[int] = []
    for a, b in params:
        minimum = min(((a * sid + b) & 0xFFFFFFFF) for sid in shingle_ids)
        signature.append(minimum)
    return tuple(signature)


def _band_key(signature: tuple[int, ...], band_index: int, rows_per_band: int) -> bytes:
    start = band_index * rows_per_band
    band = signature[start : start + rows_per_band]
    return hashlib.sha256(struct.pack(f">{len(band)}I", *band)).digest()


def _lsh_candidate_pairs(
    signatures: list[tuple[int, ...]],
    num_perm: int,
) -> set[tuple[int, int]]:
    """Return candidate index pairs from banding (b bands × r rows)."""
    # Choose r such that b = num_perm // r is reasonable.
    rows_per_band = 4 if num_perm >= 4 else 1
    while num_perm % rows_per_band != 0 and rows_per_band > 1:
        rows_per_band -= 1
    bands = num_perm // rows_per_band
    buckets: dict[tuple[int, bytes], list[int]] = defaultdict(list)
    for idx, signature in enumerate(signatures):
        for band_index in range(bands):
            key = (band_index, _band_key(signature, band_index, rows_per_band))
            buckets[key].append(idx)

    pairs: set[tuple[int, int]] = set()
    for members in buckets.values():
        if len(members) < 2:
            continue
        ordered = sorted(set(members))
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                pairs.add((ordered[i], ordered[j]))
    return pairs


def _all_pairs(n: int) -> Iterable[tuple[int, int]]:
    for i in range(n):
        for j in range(i + 1, n):
            yield i, j


def analyze_near_duplicates(
    df: pl.DataFrame,
    config: NearDuplicateConfig | None = None,
) -> NearDuplicateAnalysis:
    cfg = config or NearDuplicateConfig()
    total = df.height

    if not cfg.enabled or total == 0:
        return NearDuplicateAnalysis(
            method=NearDuplicateMethod(
                candidate_generation="disabled" if not cfg.enabled else "none",
                minhash=MinHashInfo(enabled=False, num_perm=None),
            ),
            result=NearDuplicateResult(pairs=0, records_flagged=0, record_rate=0.0),
        )

    rows = list(df.iter_rows(named=True))
    text_fields = [record_text_and_field(row) for row in rows]
    texts = [text for text, _ in text_fields]
    fields = [field for _, field in text_fields]
    exact_hashes = [hash_record(row) for row in rows]
    shingle_sets = [char_shingles(text, cfg.shingle_size) for text in texts]

    if total <= PAIRWISE_LIMIT:
        candidate_pairs = list(_all_pairs(total))
        candidate_generation = "pairwise"
        minhash = MinHashInfo(enabled=False, num_perm=None)
    else:
        signatures = [
            minhash_signature(s, cfg.num_perm, cfg.seed) for s in shingle_sets
        ]
        candidate_pairs = sorted(_lsh_candidate_pairs(signatures, cfg.num_perm))
        candidate_generation = "minhash_lsh"
        minhash = MinHashInfo(enabled=True, num_perm=cfg.num_perm)

    near_pairs = 0
    flagged: set[int] = set()
    evidence: list[NearDuplicateEvidenceItem] = []
    truncated = False
    for i, j in candidate_pairs:
        if exact_hashes[i] == exact_hashes[j]:
            continue  # counted under exact duplicates
        score = jaccard(shingle_sets[i], shingle_sets[j])
        if score < cfg.threshold:
            continue
        near_pairs += 1
        flagged.add(i)
        flagged.add(j)
        if len(evidence) < cfg.max_evidence:
            # Prefer a shared single-field label when both sides used the same source.
            field = fields[i] if fields[i] == fields[j] else None
            evidence.append(
                NearDuplicateEvidenceItem(
                    left=i,
                    right=j,
                    jaccard=round(score, 4),
                    field=field,
                )
            )
        else:
            truncated = True

    rate = len(flagged) / total if total else 0.0
    return NearDuplicateAnalysis(
        method=NearDuplicateMethod(
            candidate_generation=candidate_generation,
            minhash=minhash,
        ),
        result=NearDuplicateResult(
            pairs=near_pairs,
            records_flagged=len(flagged),
            record_rate=round(rate, 6),
            evidence=evidence,
            evidence_truncated=truncated,
        ),
    )
