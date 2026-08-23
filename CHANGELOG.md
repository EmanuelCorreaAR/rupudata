# Changelog

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
