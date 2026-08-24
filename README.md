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

Prepare GSM8K train/test JSONL (e.g. from Hugging Face `openai/gsm8k`), then inject three test questions into a copy of train:

```bash
head -n 3 gsm8k_test.jsonl > leak.jsonl
cat gsm8k_train.jsonl >> leak.jsonl

rupudata benchmark-check leak.jsonl \
  --benchmark gsm8k \
  --reference gsm8k_test.jsonl
```

Terminal output (abridged paths):

```text
╭───────────────────────────────╮
│ RupuData v0.6.6               │
│ Follow the path of your data. │
╰───────────────────────────────╯

Benchmark check: …/leak.jsonl vs GSM8K

Benchmark
──────────────────────────────
  Benchmark                GSM8K
  Reference                user_reference
  Benchmark records        1,319
  Dataset rows             7,476
  Benchmark fingerprint    rupu:a75016197e210681

Overlap
──────────────────────────────
  Exact matches                  3
  Normalized matches             3
  Near matches                   n/a (disabled)
  Status                         OVERLAP_DETECTED
  Evidence pairs (exact)         3
  Evidence pairs (normalized)    3

Evidence (sample)
──────────────────────────────
  dataset_row    reference_row    field
  0              0                question
  1              1                question
  2              2                question
```

**3 exact GSM8K test-set overlaps detected** under the configured matching methodology.

RupuData reports textual overlap. It does **not** determine why the overlap exists or certify that a model or dataset is contaminated.

Clean train vs test (no leak):

```bash
rupudata compare gsm8k_train.jsonl gsm8k_test.jsonl --text-field question
rupudata benchmark-check gsm8k_train.jsonl --benchmark gsm8k --reference gsm8k_test.jsonl
```

→ exact/normalized overlap **0**, status **`NO_OVERLAP_DETECTED`**.

Scan on the clean train split:

```bash
rupudata scan gsm8k_train.jsonl
```

```text
Dataset
──────────────────────────────
  Rows           7,473
  Format         jsonl
  Size           1.79 MB
  Columns        question
  Fingerprint    rupu:fedca4cb0fa770fe

Duplicates
──────────────────────────────
  Exact duplicates    0
  Unique records      7,473
  Duplicate rate      0.00%
  Near-dupe pairs     2
  Records flagged     4
  Near-dupe rate      0.05%
  Near threshold      0.85
  Candidates          minhash_lsh
```

Those **2 near-dupe pairs** (character shingles, Jaccard ≥ 0.85) are real GSM8K training rows — not fixtures. From `0.7.0`, `scan` JSON includes auditable evidence, e.g. `left` / `right` / `jaccard` / `field` — so a third party does not need to re-run the CLI to verify Josie → Amanda.

| Rows | Jaccard | What differs |
|------|---------|----------------|
| `1174` ↔ `7233` | 0.87 | Same “Martha / butterflies” template; different totals and which color is asked |
| `2483` ↔ `6691` | 0.93 | Same gift / cassette / headphone word problem; only the name (`Josie` → `Amanda`) |

Example (abbreviated):

```text
Record 2483
  Josie received $50 as a gift. She plans to buy two cassette tapes…

Record 6691
  Amanda received $50 as a gift. She plans to buy two cassette tapes…

Similarity (Jaccard on character shingles): 0.93
```

That is **lexical** near-duplication. RupuData does **not** claim the questions are the same math problem for a student, nor plagiarism — only that the strings share enough character shingles under the configured threshold.

```text
7,476 training records (with 3 injected test rows)
        │
        ▼
     RupuData
        │
        ├── scan (clean train): 0 exact duplicates, 2 near-dupe pairs
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

`0.7.0` — scan near-duplicate evidence in the JSON audit contract (`left` / `right` / `jaccard` / `field`).

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
