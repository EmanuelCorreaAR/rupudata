# Changelog

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

