# Changelog

## [0.3.2] - 2026-08-23
### Changed
- JSON reports now follow an explicit technical audit contract: `input → configuration → method → result`

## [0.3.1] - 2026-08-23

### Fixed
- Near-duplicate JSON report now states which candidate strategy ran (`pairwise` vs `minhash_lsh`) and only includes `num_perm` when MinHash was used
- Documented that report shape in `README.md` / `README.es.md`

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
