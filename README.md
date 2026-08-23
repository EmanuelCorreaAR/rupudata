# RupuData

Open-source, local-first CLI for inspecting and auditing datasets used in AI workflows.

**Follow the path of your data.**

Start by understanding what is inside your dataset: structure, duplicates, and a
deterministic content fingerprint — before you use it for training, fine-tuning,
or evaluation.

RupuData provides **technical signals, not legal certification.**

## Status

Pre-MVP / `0.1.0` — intentionally small.

What works today:

- `rupudata scan` on JSONL and Parquet
- Dataset stats (rows, size, columns, format)
- Deterministic content fingerprint (`rupu:…`)
- Exact duplicate detection (normalized record hashing)
- Rich terminal report + machine-readable JSON

Not in this release (on purpose):

- Near-duplicate detection (MinHash/LSH)
- Benchmark contamination checks
- Provenance / license signal detectors
- `compare` / CI gates

## Install

```bash
pip install -e ".[dev]"
```

## Quick start

```bash
rupudata scan examples/example.jsonl
```

Example output:

```text
╭──────────────────────────────────────╮
│ RupuData v0.1.0                      │
│ Follow the path of your data.        │
╰──────────────────────────────────────╯

Scanning: .../examples/example.jsonl

Dataset
──────────────────────────────
  Rows          5
  Format        jsonl
  Size          …
  Columns       text, source
  Fingerprint   rupu:…

Duplicates
──────────────────────────────
  Exact duplicates   2
  Unique records     3
  Duplicate rate     40.00%

Report written to:
…/rupudata-report.json
```

JSON report path (default `./rupudata-report.json`, or `-o`):

```bash
rupudata scan examples/example.jsonl -o reports/audit.json
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
