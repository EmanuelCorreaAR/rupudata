# RupuData

**Language:** [English](README.md) | [Español](README.es.md)

Open-source, local-first CLI for inspecting and auditing datasets used in AI workflows.

**Follow the path of your data.**

Start by understanding what is inside your dataset: structure, duplicates, overlap
between datasets, and a deterministic content fingerprint — before you use it for
training, fine-tuning, or evaluation.

RupuData provides **technical signals, not legal certification.**

## Status

`0.3.1` — intentionally small, useful per release.

What works today:

- `rupudata scan` on JSONL and Parquet
- Dataset stats (rows, size, columns, format)
- Deterministic content fingerprint (`rupu:…`)
- Exact duplicate detection (normalized record hashing)
- Near-duplicate detection (character shingles + Jaccard; MinHash/LSH for larger sets)
- `rupudata compare` — exact and normalized overlap between two datasets
- Rich terminal report + machine-readable JSON

Not in this release (on purpose):

- Semantic / paraphrase / translation matching
- Benchmark contamination adapters
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

### Near-duplicate methodology

1. Take comparable text (`text` column if present, otherwise joined string fields).
2. Build character shingles (default size 5).
3. Find candidate pairs (all pairs if ≤250 unique-scale rows; otherwise MinHash + LSH).
4. Keep pairs with Jaccard ≥ threshold that are **not** exact normalized duplicates.

This is **lexical** similarity. It will not claim two paraphrases are duplicates.

The JSON report records **what the engine actually ran**, not only the CLI defaults:

```json
"near_duplicates": {
  "similarity": "character_shingles+jaccard",
  "candidate_generation": "pairwise",
  "minhash": {
    "enabled": false,
    "num_perm": null
  }
}
```

- Small datasets (≤250 rows): `candidate_generation` is `pairwise`; MinHash is off (`num_perm` is `null`).
- Larger datasets: `candidate_generation` is `minhash_lsh`; `minhash.enabled` is `true` and `num_perm` is the value that was used (e.g. `64`).

`--num-perm` only affects scans that take the MinHash/LSH path.

Skip near-dupes when you only need exact stats:

```bash
rupudata scan dataset.parquet --skip-near-duplicates
```

JSON reports:

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
