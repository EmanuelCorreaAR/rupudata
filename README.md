# RupuData

**Language:** [English](README.md) | [Español](README.es.md)

**Follow the path of your data.**

RupuData answers an uncomfortable question: **does my training data overlap with data I use to evaluate my model?**

It detects **dataset duplicates**, **train/eval overlap**, and **benchmark overlap signals** — locally, with deterministic, machine-readable audit reports. Technical signals, not legal certification.

## Install

Requires **Python 3.9+**.

```bash
pip install rupudata
```

```bash
rupudata --help
```

## Quick start

```bash
pip install rupudata

rupudata scan dataset.jsonl
rupudata compare train.jsonl eval.jsonl
rupudata benchmark-check train.jsonl --benchmark gsm8k
```

Three commands. One goal: understand whether data overlaps where it shouldn't.

## Real-world example (GSM8K)

Against the full GSM8K **test** split as `--reference` (1,319 questions), a 7,476-row training file with three injected test questions reports:

```bash
rupudata benchmark-check leak.jsonl \
  --benchmark gsm8k \
  --reference gsm8k_test.jsonl
```

```text
RupuData v0.6.5

Dataset:       7,476 records
Reference:     GSM8K test — 1,319 records (user_reference)

Exact matches:       3
Normalized matches:  3
Near matches:        0

Status: OVERLAP_DETECTED

Evidence
  dataset_row  reference_row  field
  0            0              question
  1            1              question
  2            2              question
```

**3 exact GSM8K test-set overlaps detected** under the configured matching methodology.

RupuData reports textual overlap. It does **not** determine why the overlap exists or certify that a model or dataset is contaminated.

On the clean GSM8K **train** split (7,473 records) alone:

```bash
rupudata scan gsm8k_train.jsonl
```

→ no exact duplicates; only **2** lexical near-duplicate pairs flagged (Jaccard ≥ 0.85, MinHash/LSH).

```text
7,476 training records
        │
        ▼
     RupuData
        │
        ├── scan: 0 exact duplicates, 2 near-dupe pairs
        │
        ▼
   GSM8K test (1,319) via --reference
        │
        ▼
   3 exact overlaps → OVERLAP_DETECTED
```

### Benchmark reference: demo sample vs real audit

> **Warning:** Without `--reference`, default `gsm8k` uses a **tiny packaged sample**. A `NO_OVERLAP_DETECTED` against that sample does **not** mean your dataset is free of GSM8K. For an actual audit, pass the real export with `--reference`.

```bash
rupudata benchmark-check train.jsonl --benchmark gsm8k --reference /path/to/gsm8k.jsonl
```

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

```bash
git clone https://github.com/EmanuelCorreaAR/rupudata.git
cd rupudata
pip install rupudata

rupudata compare examples/train.jsonl examples/eval.jsonl
rupudata benchmark-check examples/train_with_gsm8k_overlap.jsonl --benchmark gsm8k
rupudata scan examples/near_dupes.jsonl --near-duplicate-threshold 0.85
```

## Status

`0.6.5` — contextual benchmark notes + real-world GSM8K README demo.

**Not in this release (on purpose):** semantic / paraphrase matching, CI fail gates, streaming multi-GB scans, provenance/license detectors.

**Next:** driven by real usage. Likely first bridge: exit codes for pipelines (`--fail-on-overlap`). Matching model stays stable unless users need a change.

## What RupuData does not do

- determine legal ownership or certify copyright compliance
- guarantee a dataset is legally safe
- detect every form of benchmark contamination
- claim semantic understanding of near-duplicates
- replace specialized license scanners or large-scale frameworks

## Technical audit contract

For readers who need to reproduce findings exactly. JSON reports are shaped so a third party can audit the method:

```text
input → configuration → method → result
```

### Matching model (source → unit → spec)

| `method.unit` | Text source | Specs |
|---------------|-------------|--------|
| `full_record` | whole record | `record_exact_v1` / `record_normalized_v1` |
| `field_text` | explicit `method.field` (`--text-field`) | `text_exact_v1` / `text_normalized_v1` |
| `extracted_text` | `text_extraction` (e.g. first_non_empty) | `text_exact_v1` / `text_normalized_v1` |

`text_*` specs define how a plain text value is hashed. They do not define where the text came from — the command declares the source.

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
