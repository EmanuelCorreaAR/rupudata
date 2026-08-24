# Technical audit contract

**Language:** [English](AUDIT.md) | [Español](AUDIT.es.md)

RupuData JSON reports follow:

```text
input → configuration → method → result
```

Reports are **technical signals, not legal certification.**

Defaults: `rupudata-report.json`, `rupudata-compare.json`, `rupudata-benchmark.json`.

## Matching model (source → unit → spec)

| `method.unit` | Text source | Specs |
|---------------|-------------|--------|
| `full_record` | whole record | `record_exact_v1` / `record_normalized_v1` |
| `field_text` | explicit `method.field` (`--text-field`) | `text_exact_v1` / `text_normalized_v1` |
| `extracted_text` | `text_extraction` (e.g. first_non_empty) | `text_exact_v1` / `text_normalized_v1` |

`text_*` specs define how a plain text value is hashed. They do not define where the text came from — the command declares the source.

## Matching vocabulary by command

| Command | Field | Spec / unit |
|---------|--------|-------------|
| `scan` | `exact_duplicates` | `record_normalized_v1` (`unit=full_record`) |
| `compare` | `exact_overlap` / `normalized_overlap` | `record_*` or `text_*` per `method.unit` |
| `benchmark-check` | `exact` / `normalized` | `text_*` with `unit=extracted_text` |

### Compare match evidence

- `matches.exact`: row pairs only (+ `field` in field_text mode). No `also_exact` / diffs.
- `matches.normalized`: always `also_exact`. When `also_exact` is false, full_record adds `differing_fields` and field_text adds `difference`; when true, diffs are omitted.

### Scan near-duplicate evidence (0.7.0+)

`result.near_duplicates` includes:

- `pairs`, `records_flagged`, `record_rate`
- `evidence[]`: `{ left, right, jaccard, field? }` (0-based rows; `field` when a single text source is used)
- `evidence_truncated`: true when more pairs exist than `--max-evidence`

Evidence documents the **finding** (which rows, which score). It does not embed full record text — open the dataset at those indices to inspect content.

## What “normalized” means (fingerprint + scan exact duplicates)

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

Near-duplicates use a **different** text prep (`near_text_v1`: lowercase + collapse whitespace on comparable text). Lexical similarity only — not paraphrases.

```bash
rupudata scan dataset.parquet --skip-near-duplicates
```
