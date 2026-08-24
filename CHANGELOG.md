# Changelog

## [0.6.5] - 2026-08-23
### Changed
- Benchmark notes are contextual to `input.reference_source` (packaged sample vs user-provided reference)
- README: real-world GSM8K demo (7k+ rows, 3 exact test overlaps) without claiming “contamination”

## [0.6.4] - 2026-08-23
### Changed
- Align PyPI package description with README wording (benchmark *overlap* signals, not contamination)

## [0.6.3] - 2026-08-23
### Added
- GitHub Actions CI: pytest on Python 3.9–3.12, wheel build, clean-venv smoke (`rupudata --help`, compare, benchmark-check)
### Changed
- Product packaging for PyPI: richer metadata, Python version classifiers, sdist includes `examples/`
- README oriented to end users (`pip install rupudata`, 60-second path: compare → benchmark-check → scan)

## [0.6.2] - 2026-08-23
### Changed
- Formalize compare match evidence shape: exact omits `also_exact`/diffs; normalized always has `also_exact` and includes `differing_fields`/`difference` only when `also_exact` is false

## [0.6.1] - 2026-08-23
### Changed
- Unify `method.unit` as matching category: `full_record` | `field_text` | `extracted_text`
- Compare text mode exposes `method.field`; evidence uses `difference` (not `differing_fields`)
- Drop encyclopedic matching-vocabulary notes from reports (taxonomy lives in README)
- Remove competing `unit` from `text_extraction` (source strategy only)

## [0.6.0] - 2026-08-23
### Added
- `rupudata compare --text-field NAME` for field-level text overlap (`unit=field_text`, `text_exact_v1` / `text_normalized_v1`)
### Changed
- `text_*` specs define plain-text transforms only; text source is declared by the command (`field_text` vs `text_extraction`)

## [0.5.2] - 2026-08-23
### Added
- Contract hardening tests: whitespace invariants for record_*/text_* and command-specific method specs

## [0.5.1] - 2026-08-23
### Changed
- Benchmark: `text_normalization` → `text_normalized`; specs include `base_normalization`
- Scan/compare: `method.record_normalization` → `method.record_normalized` (pairs with `record_exact` / `text_exact` / `text_normalized`)

## [0.5.0] - 2026-08-23
### Removed
- Deprecated `method.comparable_fields` alias (use `method.text_extraction.candidate_fields`)
### Changed
- Benchmark matching specs are now `text_exact_v1` / `text_normalized_v1` (extracted text unit), distinct from full-record `record_*_v1`

## [0.4.7] - 2026-08-23
### Changed
- Document that "exact" is command-specific: scan `exact_duplicates` uses `record_normalized_v1`; compare `exact_overlap` uses `record_exact_v1`

## [0.4.6] - 2026-08-23
### Changed
- Align scan / compare / benchmark-check audit contracts (shared notes, fingerprint id, row_index_base, evidence limits)

## [0.4.5] - 2026-08-23
### Added
- Compare: `also_exact` + `differing_fields` on normalized match evidence (raw field equality)
- CLI `--max-evidence` for compare evidence pair cap

## [0.4.4] - 2026-08-23
### Added
- Compare match evidence: per-pair `dataset_a_record` / `dataset_b_record` (0-based), parallel to benchmark-check

## [0.4.3] - 2026-08-23
### Changed
- Benchmark method uses `text_extraction` (`strategy`, `candidate_fields`); `comparable_fields` kept as a deprecated alias

## [0.4.2] - 2026-08-23
### Added
- Benchmark-check match evidence: per-pair `dataset_record`, `reference_record`, and `field` (0-based rows)

## [0.4.1] - 2026-08-23
### Changed
- Refactor benchmark support behind a `BenchmarkAdapter` protocol; GSM8K is the first adapter

## [0.4.0] - 2026-08-23
### Added
- CLI `rupudata benchmark-check` for exact/normalized text overlap vs registered benchmarks
- Built-in `gsm8k` sample reference (demo/CI only; use `--reference` for full corpora)

## [0.3.4] - 2026-08-23
### Changed
- Near-duplicate config/method now report `shingle: { unit, size }` instead of ambiguous `shingle_size`

## [0.3.3] - 2026-08-23
### Added
- Explicit `record_normalization` / `record_exact` / near-dupe `text_prep` specs in the audit JSON

## [0.3.2] - 2026-08-23
### Changed
- JSON reports now follow an explicit technical audit contract: `input → configuration → method → result`

## [0.3.1] - 2026-08-23

### Fixed
- Near-duplicate JSON report now states which candidate strategy ran (`pairwise` vs `minhash_lsh`) and only includes `num_perm` when MinHash was used

## [0.3.0] - 2026-08-23

### Added
- Near-duplicate detection in `rupudata scan` (character shingles + Jaccard)
- MinHash + LSH candidate generation for larger datasets (pairwise below 250 rows)
- CLI flags: `--near-duplicate-threshold`, `--shingle-size`, `--num-perm`, `--skip-near-duplicates`
- Example fixture `examples/near_dupes.jsonl`

## [0.2.0] - 2026-08-23

### Added
- CLI `rupudata compare` for exact and normalized record overlap between two datasets
- Example train/eval fixtures demonstrating whitespace-normalized overlap
- Structured JSON compare report (`rupudata-compare.json` by default)

## [0.1.0] - 2026-08-23

### Added
- CLI `rupudata scan` for JSONL and Parquet datasets
- Dataset stats (rows, size, columns, format)
- Deterministic content fingerprint (`rupu:…`)
- Exact duplicate detection with record normalization
- Rich terminal report and machine-readable JSON output
- Example fixture and test suite
