# RupuData

Open-source, local-first CLI for inspecting and auditing datasets used in AI workflows.

**Follow the path of your data.**

Start by understanding what is inside your dataset: structure, duplicates, overlap
between datasets, and a deterministic content fingerprint — before you use it for
training, fine-tuning, or evaluation.

RupuData provides **technical signals, not legal certification.**

## Status

`0.2.0` — intentionally small, useful per release.

What works today:

- `rupudata scan` on JSONL and Parquet
- Dataset stats (rows, size, columns, format)
- Deterministic content fingerprint (`rupu:…`)
- Exact duplicate detection (normalized record hashing)
- `rupudata compare` — exact and normalized overlap between two datasets
- Rich terminal report + machine-readable JSON

Not in this release (on purpose):

- Near-duplicate detection (MinHash/LSH)
- Benchmark contamination adapters
- Provenance / license signal detectors
- CI gates

## Install

```bash
pip install -e ".[dev]"
```

## Quick start

### Scan

```bash
rupudata scan examples/example.jsonl
```

### Compare

```bash
rupudata compare examples/train.jsonl examples/eval.jsonl
```

Example compare output:

```text
Dataset Diff

  Path          …/train.jsonl    …/eval.jsonl
  Rows          4                4
  Fingerprint   rupu:…           rupu:…

Overlap
──────────────────────────────
  Exact overlap          1
  Normalized overlap     2
  Only in A (exact)      3
  Only in B (exact)      3
```

Exact = stable record hash without stripping strings.  
Normalized = same after light normalization (e.g. strip whitespace).

This reports **technical overlap**, not paraphrases, translations, or semantic contamination.

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
- replace specialized license scanners or large-scale processing frameworks

That honesty is intentional.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

Apache License 2.0
