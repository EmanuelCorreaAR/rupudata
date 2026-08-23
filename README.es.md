# RupuData

**Idioma:** [English](README.md) | [Español](README.es.md)

CLI open-source y local-first para inspeccionar y auditar datasets usados en flujos de AI.

**Follow the path of your data.**

Empezá por entender qué hay dentro de tu dataset: estructura, duplicados, solapamiento
entre datasets y un fingerprint de contenido determinístico — antes de usarlo para
entrenamiento, fine-tuning o evaluación.

RupuData ofrece **señales técnicas, no certificación legal.**

## Estado

`0.3.1` — deliberadamente chico; cada release aporta algo útil.

Qué funciona hoy:

- `rupudata scan` sobre JSONL y Parquet
- Stats del dataset (filas, tamaño, columnas, formato)
- Fingerprint de contenido determinístico (`rupu:…`)
- Detección de duplicados exactos (hash de registros normalizados)
- Detección de near-duplicates (character shingles + Jaccard; MinHash/LSH en sets más grandes)
- `rupudata compare` — overlap exacto y normalizado entre dos datasets
- Reporte Rich en terminal + JSON estructurado

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

### Metodología de near-duplicates

1. Tomar texto comparable (columna `text` si existe; si no, campos string unidos).
2. Armar character shingles (tamaño por defecto 5).
3. Buscar pares candidatos (todos los pares si ≤250 filas; si no, MinHash + LSH).
4. Conservar pares con Jaccard ≥ umbral que **no** sean duplicados exactos normalizados.

Esto mide similitud **léxica**. No afirma que dos paráfrasis sean duplicados.

Omitir near-dupes si solo necesitás stats exactas:

```bash
rupudata scan dataset.parquet --skip-near-duplicates
```

Reportes JSON:

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
