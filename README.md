# RupuData

**Language:** [English](README.md) | [Español](README.es.md)

Open-source, local-first CLI for inspecting and auditing datasets used in AI workflows.

**Follow the path of your data.**

Start by understanding what is inside your dataset: structure, duplicates, overlap
between datasets, and a deterministic content fingerprint — before you use it for
training, fine-tuning, or evaluation.

RupuData provides **technical signals, not legal certification.**

## Status

`0.6.0` — intentionally small, useful per release.

What works today:

- `rupudata scan` on JSONL and Parquet
- Dataset stats (rows, size, columns, format)
- Deterministic content fingerprint (`rupu:…`)
- Exact duplicate detection (normalized record hashing)
- Near-duplicate detection (character shingles + Jaccard; MinHash/LSH for larger sets)
- `rupudata compare` — exact and normalized overlap between two datasets, with per-match row evidence (full record or `--text-field`)
- `rupudata benchmark-check` — exact/normalized overlap vs a benchmark reference (e.g. GSM8K sample), with per-match evidence (row + field)
- Machine-readable **technical audit contract** JSON (`input → configuration → method → result`)

Not in this release (on purpose):

- Semantic / paraphrase / translation matching
- Near-duplicate matching against benchmarks
- Provenance / license signal detectors
- CI gates
- Streaming scans for multi-GB datasets

## Install

```bash
pip install -e ".[dev]"
```

## Quick start

### Scan

```bash
rupudata scan examples/example.jsonl
rupudata scan examples/near_dupes.jsonl --near-duplicate-threshold 0.85
```

### Compare

```bash
rupudata compare examples/train.jsonl examples/eval.jsonl
```

Compares **full records** by default (`unit=full_record`). With `--text-field NAME`, compares that column via `text_exact_v1` / `text_normalized_v1` (`unit=field_text`). Cap evidence with `--max-evidence`.

```bash
rupudata compare examples/train.jsonl examples/eval.jsonl --text-field text
```

### Benchmark check

```bash
rupudata benchmark-check examples/train_with_gsm8k_overlap.jsonl --benchmark gsm8k
```

Reports exact and normalized text overlap against a benchmark reference.  
Default `gsm8k` uses a **tiny packaged sample** (demos/tests). For real audits:

```bash
rupudata benchmark-check train.jsonl --benchmark gsm8k --reference /path/to/gsm8k.jsonl
```

Status is `OVERLAP_DETECTED` or `NO_OVERLAP_DETECTED` under the matching methodology — **not** a claim that a model is contaminated.

Benchmarks are pluggable via a `BenchmarkAdapter` interface (`load_reference`, `candidate_fields`). Only **GSM8K** is registered today.

Matching uses **text extraction**, not full-record comparison: one comparison text per record via `first_non_empty` over `candidate_fields` (`question`, `problem`, `prompt`, `text`). Remaining fields are ignored. Evidence includes the selected `field`.

## Technical audit contract

JSON reports are shaped so a third party can reproduce the finding:

```text
input → configuration → method → result
```

`scan`, `compare`, and `benchmark-check` share this shell, the same fingerprint id (`normalized_record_multiset_sha256`), shared row-index rules, and common disclaimers. Matching **units** differ by command (`record_*` vs `text_*`).

### Matching vocabulary (units are command-specific)

| Command | Field | Spec / unit |
|---------|--------|-------------|
| `scan` | `exact_duplicates` | `record_normalized_v1` (full record; same transforms as fingerprint) |
| `compare` | `exact_overlap` / `normalized_overlap` | `record_*` when `unit=full_record`; `text_*` when `unit=field_text` |
| `benchmark-check` | `exact` / `normalized` | `text_*` after `text_extraction` (source ≠ field_text) |

`text_exact_v1` / `text_normalized_v1` define how a plain text value is hashed. The text **source** is separate: explicit `--text-field`, or benchmark `text_extraction`.

Example (`scan`):

```json
{
  "contract": "technical_audit",
  "disclaimer": "Technical signals, not legal certification.",
  "input": { "rows": 5, "format": "jsonl", "path": "..." },
  "configuration": {
    "near_duplicates": {
      "enabled": true,
      "threshold": 0.85,
      "shingle": { "unit": "character", "size": 5 },
      "num_perm": 64
    }
  },
  "method": {
    "fingerprint": "normalized_record_multiset_sha256",
    "exact_duplicates": "record_normalized_v1 / normalized_record_sha256 (NOT compare exact_overlap / record_exact_v1)",
    "record_normalized": {
      "id": "record_normalized_v1",
      "string_strip": true,
      "collapse_internal_whitespace": false,
      "case_fold": false,
      "unicode_normalize": null
    },
    "near_duplicates": {
      "similarity": "character_shingles+jaccard",
      "candidate_generation": "pairwise",
      "shingle": { "unit": "character", "size": 5 },
      "minhash": { "enabled": false, "num_perm": null },
      "text_prep": { "id": "near_text_v1", "lowercase": true, "collapse_whitespace": true }
    }
  },
  "result": {
    "fingerprint": "rupu:…",
    "exact_duplicates": { "duplicate_records": 0, "duplicate_rate": 0.0 },
    "near_duplicates": { "pairs": 1, "records_flagged": 2, "record_rate": 0.4 }
  }
}
```

- `configuration` = what you asked for (CLI intent).
- `method` = what actually ran (`pairwise` vs `minhash_lsh`; `num_perm` only when MinHash ran).
- `result` = reproducible numeric evidence under that method.

### What “normalized” means (fingerprint + exact duplicates)

Policy id: `record_normalized_v1` (also under `method.record_normalized` in the JSON).

| Step | Behavior |
|---|---|
| Fields | **All** record fields are included (no column exclusions) |
| Keys | Object keys sorted recursively |
| Strings | `str.strip()` only (leading/trailing whitespace) |
| Internal spaces | **Kept** — `" Hello   World "` → `"Hello   World"` |
| Case | **Not** lowercased |
| Unicode | **No** NFC/NFKC normalization |
| Serialize | Compact UTF-8 JSON, sorted keys |
| Hash | SHA-256 |

Fingerprint = SHA-256 over the **sorted multiset** of per-record hashes, then `rupu:` + 16 hex chars.

Near-duplicates use a **different** text prep (`near_text_v1`: lowercase + collapse whitespace on the comparable text). That does **not** change the fingerprint.

This is intentionally **not** a legal opinion.

### Near-duplicate methodology

1. Take comparable text (`text` column if present, otherwise joined string fields).
2. Build character shingles (default size 5).
3. Find candidate pairs (all pairs if ≤250 rows; otherwise MinHash + LSH).
4. Keep pairs with Jaccard ≥ threshold that are **not** exact normalized duplicates.

This is **lexical** similarity. It will not claim two paraphrases are duplicates.

`--num-perm` only affects scans that take the MinHash/LSH path.

```bash
rupudata scan dataset.parquet --skip-near-duplicates
```

```bash
rupudata scan examples/example.jsonl -o reports/audit.json
rupudata compare examples/train.jsonl examples/eval.jsonl -o reports/compare.json
```

## What RupuData does not do

RupuData does not:

- determine legal ownership
- certify copyright compliance
- guarantee that a dataset is legally safe
- detect every form of benchmark contamination
- claim semantic understanding of every near-duplicate
- replace specialized license scanners or large-scale processing frameworks

That honesty is intentional.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

Apache License 2.0
