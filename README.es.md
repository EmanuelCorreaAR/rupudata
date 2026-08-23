# RupuData

**Idioma:** [English](README.md) | [Español](README.es.md)

CLI open-source y local-first para inspeccionar y auditar datasets usados en flujos de AI.

**Follow the path of your data.**

Empezá por entender qué hay dentro de tu dataset: estructura, duplicados, solapamiento
entre datasets y un fingerprint de contenido determinístico — antes de usarlo para
entrenamiento, fine-tuning o evaluación.

RupuData ofrece **señales técnicas, no certificación legal.**

## Estado

`0.3.2` — deliberadamente chico; cada release aporta algo útil.

Qué funciona hoy:

- `rupudata scan` sobre JSONL y Parquet
- Stats del dataset (filas, tamaño, columnas, formato)
- Fingerprint de contenido determinístico (`rupu:…`)
- Detección de duplicados exactos (hash de registros normalizados)
- Detección de near-duplicates (character shingles + Jaccard; MinHash/LSH en sets más grandes)
- `rupudata compare` — overlap exacto y normalizado entre dos datasets
- JSON como **contrato de auditoría técnica** (`input → configuration → method → result`)

Qué no entra en este release (a propósito):

- Matching semántico / paráfrasis / traducciones
- Adapters de contaminación de benchmarks
- Detectores de provenance / licencias
- Gates de CI
- Scans streaming para datasets de varios GB

## Instalación

```bash
pip install -e ".[dev]"
```

## Inicio rápido

### Scan

```bash
rupudata scan examples/example.jsonl
rupudata scan examples/near_dupes.jsonl --near-duplicate-threshold 0.85
```

### Compare

```bash
rupudata compare examples/train.jsonl examples/eval.jsonl
```

## Contrato de auditoría técnica

Los reportes JSON están pensados para que un tercero pueda reproducir el hallazgo:

```text
input → configuration → method → result
```

Ejemplo (`scan`):

```json
{
  "contract": "technical_audit",
  "disclaimer": "Technical signals, not legal certification.",
  "input": { "rows": 5, "format": "jsonl", "path": "..." },
  "configuration": {
    "near_duplicates": {
      "enabled": true,
      "threshold": 0.85,
      "shingle_size": 5,
      "num_perm": 64
    }
  },
  "method": {
    "fingerprint": "normalized_record_multiset_sha256",
    "exact_duplicates": "normalized_record_sha256",
    "near_duplicates": {
      "similarity": "character_shingles+jaccard",
      "candidate_generation": "pairwise",
      "minhash": { "enabled": false, "num_perm": null }
    }
  },
  "result": {
    "fingerprint": "rupu:…",
    "exact_duplicates": { "duplicate_records": 0, "duplicate_rate": 0.0 },
    "near_duplicates": { "pairs": 1, "records_flagged": 2, "record_rate": 0.4 }
  }
}
```

- `configuration` = lo que pediste (intención del CLI).
- `method` = lo que corrió de verdad (`pairwise` vs `minhash_lsh`; `num_perm` solo si MinHash corrió).
- `result` = evidencia numérica reproducible bajo ese método.

Esto **no** es una opinión legal.

### Metodología de near-duplicates

1. Tomar texto comparable (columna `text` si existe; si no, campos string unidos).
2. Armar character shingles (tamaño por defecto 5).
3. Buscar pares candidatos (todos los pares si ≤250 filas; si no, MinHash + LSH).
4. Conservar pares con Jaccard ≥ umbral que **no** sean duplicados exactos normalizados.

Esto mide similitud **léxica**. No afirma que dos paráfrasis sean duplicados.

`--num-perm` solo afecta scans que toman el camino MinHash/LSH.

```bash
rupudata scan dataset.parquet --skip-near-duplicates
```

```bash
rupudata scan examples/example.jsonl -o reports/audit.json
rupudata compare examples/train.jsonl examples/eval.jsonl -o reports/compare.json
```

## Qué RupuData no hace

RupuData no:

- determina propiedad legal
- certifica cumplimiento de copyright
- garantiza que un dataset sea legalmente seguro
- detecta toda forma de contaminación de benchmarks
- afirma comprensión semántica de cada near-duplicate
- reemplaza scanners de licencias especializados ni frameworks de procesamiento a gran escala

Esa honestidad es intencional.

## Desarrollo

```bash
pip install -e ".[dev]"
pytest
```

## Licencia

Apache License 2.0
