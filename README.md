# RupuData

**Language:** [English](README.md) | [Español](README.es.md)

Open-source, local-first CLI for inspecting and auditing datasets used in AI workflows.

**Follow the path of your data.**

Start by understanding what is inside your dataset: structure, duplicates, overlap
between datasets, and a deterministic content fingerprint — before you use it for
training, fine-tuning, or evaluation.

RupuData provides **technical signals, not legal certification.**

## Status

`0.3.2` — intentionally small, useful per release.

What works today:

- `rupudata scan` on JSONL and Parquet
- Dataset stats (rows, size, columns, format)
- Deterministic content fingerprint (`rupu:…`)
- Exact duplicate detection (normalized record hashing)
- Near-duplicate detection (character shingles + Jaccard; MinHash/LSH for larger sets)
- `rupudata compare` — exact and normalized overlap between two datasets
- Machine-readable **technical audit contract** JSON (`input → configuration → method → result`)

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

## Technical audit contract

JSON reports are shaped so a third party can reproduce the finding:

```text
input → configuration → method → result
```

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
      "shingle_size": 5,
      "num_perm": 64
    }
  },
  "method": {
    "fingerprint": "normalized_record_multiset_sha256",
    "exact_duplicates": "normalized_record_sha256",
    "near_duplicates": {
      "similarity": "character_shingles+jaccard",
      "candidate_generation": "pairwise",
      "minhash": { "enabled": false, "num_perm": null }
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
