# RupuData

**Language:** [English](README.md) | [Español](README.es.md)

**Follow the path of your data.**

RupuData detects **dataset overlap**, **duplicates**, and **benchmark contamination signals** — locally, with deterministic machine-readable audit reports.

Compare datasets, scan for duplicates, and check whether training data overlaps known evaluation benchmarks. Technical signals, not legal certification.

## Install

Requires **Python 3.9+**.

```bash
pip install rupudata
```

```bash
rupudata --help
```

## Quick start

### Check train ↔ eval overlap

```bash
rupudata compare train.jsonl eval.jsonl
```

Example (from the repo `examples/`):

```text
RupuData v0.6.3

Exact overlap:       1
Normalized overlap:  2

Evidence (sample)
  dataset_a_row  dataset_b_row
  0              0
```

### Check overlap with a known benchmark

```bash
rupudata benchmark-check train.jsonl --benchmark gsm8k
```

Status is `OVERLAP_DETECTED` or `NO_OVERLAP_DETECTED` under the matching methodology — **not** a claim that a model is contaminated.

Default `gsm8k` uses a **tiny packaged sample** (demos/tests). For real audits, pass your reference:

```bash
rupudata benchmark-check train.jsonl --benchmark gsm8k --reference /path/to/gsm8k.jsonl
```

### Scan one dataset

```bash
rupudata scan dataset.jsonl
```

Stats, fingerprint (`rupu:…`), exact duplicates, and lexical near-duplicates (JSONL / Parquet).

## What each command answers

```text
scan
  → Do I have duplicates?

compare
  → Do train and eval share data?

benchmark-check
  → Does my dataset contain known benchmark text?
```

## Formats & reports

- Input: **JSONL** and **Parquet**
- Output: terminal summary + JSON audit contract (`input → configuration → method → result`)
- Defaults: `rupudata-report.json`, `rupudata-compare.json`, `rupudata-benchmark.json`

```bash
rupudata compare a.jsonl b.jsonl -o reports/compare.json
```

Compare full records by default. For a single text column:

```bash
rupudata compare train.jsonl eval.jsonl --text-field text
```

## Try the packaged examples

Clone the repo (or download `examples/` from GitHub):

```bash
git clone https://github.com/EmanuelCorreaAR/rupudata.git
cd rupudata
pip install rupudata

rupudata compare examples/train.jsonl examples/eval.jsonl
rupudata benchmark-check examples/train_with_gsm8k_overlap.jsonl --benchmark gsm8k
rupudata scan examples/near_dupes.jsonl --near-duplicate-threshold 0.85
```

## Status

`0.6.3` — product release: install from PyPI, user-facing docs, CI.

**Not in this release (on purpose):** semantic / paraphrase matching, CI fail gates, streaming multi-GB scans, provenance/license detectors.

**Next:** driven by real usage. Likely first bridge: exit codes for pipelines (`--fail-on-overlap`). Matching model stays stable unless users need a change.

## Technical audit contract

JSON reports are shaped so a third party can reproduce the finding:

```text
input → configuration → method → result
```

### Matching model (source → unit → spec)

| `method.unit` | Text source | Specs |
|---------------|-------------|--------|
| `full_record` | whole record | `record_exact_v1` / `record_normalized_v1` |
| `field_text` | explicit `method.field` (`--text-field`) | `text_exact_v1` / `text_normalized_v1` |
| `extracted_text` | `text_extraction` (e.g. first_non_empty) | `text_exact_v1` / `text_normalized_v1` |

`text_*` specs define how a plain text value is hashed. They do not define where the text came from.

### Matching vocabulary by command

| Command | Field | Spec / unit |
|---------|--------|-------------|
| `scan` | `exact_duplicates` | `record_normalized_v1` (`unit=full_record`) |
| `compare` | `exact_overlap` / `normalized_overlap` | `record_*` or `text_*` per `method.unit` |
| `benchmark-check` | `exact` / `normalized` | `text_*` with `unit=extracted_text` |

Compare match evidence: `exact` lists row pairs only; `normalized` always includes `also_exact`, and adds `differing_fields` (full record) or `difference` (field text) only when `also_exact` is false.

### What “normalized” means (fingerprint + scan exact duplicates)

Policy id: `record_normalized_v1`.

| Step | Behavior |
|---|---|
| Fields | **All** record fields |
| Keys | Sorted recursively |
| Strings | `str.strip()` only |
| Internal spaces | **Kept** |
| Case / Unicode | No lowercasing, no NFC/NFKC |
| Hash | SHA-256 over compact sorted JSON |

Fingerprint = SHA-256 over the **sorted multiset** of per-record hashes → `rupu:` + 16 hex chars.

Near-duplicates use a **different** text prep (`near_text_v1`: lowercase + collapse whitespace). Lexical similarity only — not paraphrases.

```bash
rupudata scan dataset.parquet --skip-near-duplicates
```

## What RupuData does not do

- determine legal ownership or certify copyright compliance
- guarantee a dataset is legally safe
- detect every form of benchmark contamination
- claim semantic understanding of near-duplicates
- replace specialized license scanners or large-scale frameworks

## Development

```bash
git clone https://github.com/EmanuelCorreaAR/rupudata.git
cd rupudata
pip install -e ".[dev]"
pytest
python -m build
```

## License

Apache License 2.0
