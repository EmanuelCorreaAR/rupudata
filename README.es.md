# RupuData

**Idioma:** [English](README.md) | [Español](README.es.md)

**Follow the path of your data.**

RupuData detecta **overlap entre datasets**, **duplicados** y **señales de contaminación con benchmarks** — en local, con reportes de auditoría deterministas y legibles por máquina.

Compará datasets, escaneá duplicados y verificá si tu training data solapa benchmarks de evaluación conocidos. Señales técnicas, no certificación legal.

## Instalación

Requiere **Python 3.9+**.

```bash
pip install rupudata
```

```bash
rupudata --help
```

## Inicio rápido

### Overlap train ↔ eval

```bash
rupudata compare train.jsonl eval.jsonl
```

Ejemplo (desde `examples/` del repo):

```text
RupuData v0.6.3

Exact overlap:       1
Normalized overlap:  2

Evidence (sample)
  dataset_a_row  dataset_b_row
  0              0
```

### Overlap con un benchmark conocido

```bash
rupudata benchmark-check train.jsonl --benchmark gsm8k
```

El status es `OVERLAP_DETECTED` o `NO_OVERLAP_DETECTED` bajo la metodología — **no** una afirmación de que el modelo está contaminado.

Por defecto `gsm8k` usa un **sample empaquetado** (demos/tests). Para auditorías reales:

```bash
rupudata benchmark-check train.jsonl --benchmark gsm8k --reference /path/to/gsm8k.jsonl
```

### Escanear un dataset

```bash
rupudata scan dataset.jsonl
```

Stats, fingerprint (`rupu:…`), duplicados exactos y near-duplicates léxicos (JSONL / Parquet).

## Qué responde cada comando

```text
scan
  → ¿Tengo duplicados?

compare
  → ¿Train y eval comparten datos?

benchmark-check
  → ¿Mi dataset contiene texto de benchmarks conocidos?
```

## Formatos y reportes

- Entrada: **JSONL** y **Parquet**
- Salida: resumen en terminal + contrato JSON (`input → configuration → method → result`)
- Defaults: `rupudata-report.json`, `rupudata-compare.json`, `rupudata-benchmark.json`

```bash
rupudata compare a.jsonl b.jsonl -o reports/compare.json
```

Por defecto compara registros completos. Para una sola columna de texto:

```bash
rupudata compare train.jsonl eval.jsonl --text-field text
```

## Probar los ejemplos del repo

```bash
git clone https://github.com/EmanuelCorreaAR/rupudata.git
cd rupudata
pip install rupudata

rupudata compare examples/train.jsonl examples/eval.jsonl
rupudata benchmark-check examples/train_with_gsm8k_overlap.jsonl --benchmark gsm8k
rupudata scan examples/near_dupes.jsonl --near-duplicate-threshold 0.85
```

## Estado

`0.6.3` — release de producto: instalación desde PyPI, docs de usuario, CI.

**No en este release (a propósito):** matching semántico / paráfrasis, gates de CI, scans streaming multi-GB, detectores de provenance/licencia.

**Siguiente:** según uso real. Puente probable: códigos de salida para pipelines (`--fail-on-overlap`). El modelo de matching se mantiene estable salvo que haga falta.

## Contrato de auditoría técnica

Los reportes JSON permiten que un tercero reproduzca el hallazgo:

```text
input → configuration → method → result
```

### Modelo de matching (fuente → unit → spec)

| `method.unit` | Fuente de texto | Specs |
|---------------|-----------------|--------|
| `full_record` | registro completo | `record_exact_v1` / `record_normalized_v1` |
| `field_text` | `method.field` explícito (`--text-field`) | `text_exact_v1` / `text_normalized_v1` |
| `extracted_text` | `text_extraction` (p. ej. first_non_empty) | `text_exact_v1` / `text_normalized_v1` |

Las specs `text_*` definen cómo se hashea un texto plano. No definen de dónde salió ese texto.

### Vocabulario por comando

| Comando | Campo | Spec / unit |
|---------|--------|-------------|
| `scan` | `exact_duplicates` | `record_normalized_v1` (`unit=full_record`) |
| `compare` | `exact_overlap` / `normalized_overlap` | `record_*` o `text_*` según `method.unit` |
| `benchmark-check` | `exact` / `normalized` | `text_*` con `unit=extracted_text` |

Evidencia de compare: `exact` solo pares de filas; `normalized` siempre incluye `also_exact`, y agrega `differing_fields` o `difference` solo si `also_exact` es false.

### Qué significa “normalized” (fingerprint + exact duplicates de scan)

Policy id: `record_normalized_v1`.

| Paso | Comportamiento |
|---|---|
| Campos | **Todos** |
| Keys | Ordenadas recursivamente |
| Strings | Solo `str.strip()` |
| Espacios internos | **Se conservan** |
| Case / Unicode | Sin lowercasing ni NFC/NFKC |
| Hash | SHA-256 sobre JSON compacto ordenado |

Fingerprint = SHA-256 del **multiset ordenado** de hashes por registro → `rupu:` + 16 hex.

Near-duplicates usan otra prep (`near_text_v1`). Solo similitud léxica.

```bash
rupudata scan dataset.parquet --skip-near-duplicates
```

## Qué no hace RupuData

- determinar propiedad legal ni certificar copyright
- garantizar que un dataset es legalmente seguro
- detectar toda forma de contaminación de benchmarks
- afirmar comprensión semántica de near-duplicates
- reemplazar scanners de licencia o frameworks a gran escala

## Desarrollo

```bash
git clone https://github.com/EmanuelCorreaAR/rupudata.git
cd rupudata
pip install -e ".[dev]"
pytest
python -m build
```

## Licencia

Apache License 2.0
