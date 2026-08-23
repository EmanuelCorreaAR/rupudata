# RupuData

**Idioma:** [English](README.md) | [Español](README.es.md)

CLI open-source y local-first para inspeccionar y auditar datasets usados en flujos de AI.

**Follow the path of your data.**

Empezá por entender qué hay dentro de tu dataset: estructura, duplicados, solapamiento
entre datasets y un fingerprint de contenido determinístico — antes de usarlo para
entrenamiento, fine-tuning o evaluación.

RupuData ofrece **señales técnicas, no certificación legal.**

## Estado

`0.4.5` — deliberadamente chico; cada release aporta algo útil.

Qué funciona hoy:

- `rupudata scan` sobre JSONL y Parquet
- Stats del dataset (filas, tamaño, columnas, formato)
- Fingerprint de contenido determinístico (`rupu:…`)
- Detección de duplicados exactos (hash de registros normalizados)
- Detección de near-duplicates (character shingles + Jaccard; MinHash/LSH en sets más grandes)
- `rupudata compare` — overlap exacto y normalizado entre dos datasets, con evidencia por fila
- `rupudata benchmark-check` — overlap exacto/normalizado vs un reference de benchmark (p. ej. sample GSM8K), con evidencia por match (fila + campo)
- JSON como **contrato de auditoría técnica** (`input → configuration → method → result`)

Qué no entra en este release (a propósito):

- Matching semántico / paráfrasis / traducciones
- Near-duplicates contra benchmarks
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

Compara **registros completos** (todos los campos) con hashing exacto y normalizado, y evidencia de pares de filas en `result.matches`. Los overlaps solo-normalizados incluyen `differing_fields` (valores raw). Tope de evidencia con `--max-evidence`. No es extracción de texto (a diferencia de `benchmark-check`).

### Benchmark check

```bash
rupudata benchmark-check examples/train_with_gsm8k_overlap.jsonl --benchmark gsm8k
```

Reporta overlap exacto y normalizado contra un reference de benchmark.  
Por defecto `gsm8k` usa un **sample empaquetado** (demos/tests). Para auditorías reales:

```bash
rupudata benchmark-check train.jsonl --benchmark gsm8k --reference /path/to/gsm8k.jsonl
```

El status es `OVERLAP_DETECTED` o `NO_OVERLAP_DETECTED` bajo la metodología — **no** una afirmación de que el modelo está contaminado.

Los benchmarks son plugins vía `BenchmarkAdapter` (`load_reference`, `candidate_fields`). Hoy solo está registrado **GSM8K**.

El matching usa **extracción de texto**, no comparación del registro completo: un texto de comparación por registro vía `first_non_empty` sobre `candidate_fields` (`question`, `problem`, `prompt`, `text`). El resto de campos se ignora. La evidencia incluye el `field` seleccionado.

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
      "shingle": { "unit": "character", "size": 5 },
      "num_perm": 64
    }
  },
  "method": {
    "fingerprint": "normalized_record_multiset_sha256",
    "exact_duplicates": "normalized_record_sha256",
    "record_normalization": {
      "id": "record_normalized_v1",
      "string_strip": true,
      "collapse_internal_whitespace": false,
      "case_fold": false,
      "unicode_normalize": null
    },
    "near_duplicates": {
      "similarity": "character_shingles+jaccard",
      "candidate_generation": "pairwise",
      "shingle": { "unit": "character", "size": 5 },
      "minhash": { "enabled": false, "num_perm": null },
      "text_prep": { "id": "near_text_v1", "lowercase": true, "collapse_whitespace": true }
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

### Qué significa “normalized” (fingerprint + exact duplicates)

Policy id: `record_normalized_v1` (también en `method.record_normalization` del JSON).

| Paso | Comportamiento |
|---|---|
| Campos | Se incluyen **todos** (sin excluir columnas) |
| Keys | Keys de objetos ordenadas recursivamente |
| Strings | Solo `str.strip()` (whitespace al inicio/fin) |
| Espacios internos | **Se conservan** — `" Hello   World "` → `"Hello   World"` |
| Mayúsculas | **No** se pasa a minúsculas |
| Unicode | **Sin** NFC/NFKC |
| Serialize | JSON UTF-8 compacto, keys ordenadas |
| Hash | SHA-256 |

Fingerprint = SHA-256 sobre el **multiset ordenado** de hashes por record, luego `rupu:` + 16 hex.

Near-duplicates usan **otra** prep de texto (`near_text_v1`: lowercase + colapsar whitespace). Eso **no** cambia el fingerprint.

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
