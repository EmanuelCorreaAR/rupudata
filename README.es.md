# RupuData

**Idioma:** [English](README.md) | [Español](README.es.md)

**Follow the path of your data.**

RupuData detecta **duplicados en datasets**, **overlap train/eval** y **señales de overlap con benchmarks** — en local, con reportes de auditoría deterministas y legibles por máquina.

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

```bash
pip install rupudata

rupudata scan dataset.jsonl
rupudata compare train.jsonl eval.jsonl
rupudata benchmark-check train.jsonl --benchmark gsm8k
```

Tres comandos. Un objetivo: entender si los datos se solapan donde no deberían.

### Ejemplo de salida (`compare`)

Desde `examples/` del repo:

```text
RupuData v0.6.4

Exact overlap:       1
Normalized overlap:  2

Evidence (sample)
  dataset_a_row  dataset_b_row
  0              0
```

### Reference de benchmark: sample demo vs auditoría real

El status es `OVERLAP_DETECTED` o `NO_OVERLAP_DETECTED` bajo la metodología — **no** una afirmación de que el modelo está contaminado.

> **Advertencia:** El reference GSM8K empaquetado es un **sample de demo diminuto**, no el benchmark completo. Un `NO_OVERLAP_DETECTED` contra el sample **no** significa que tu dataset esté libre de GSM8K. Para una auditoría real, pasá el export del benchmark con `--reference`.

```bash
rupudata benchmark-check train.jsonl --benchmark gsm8k --reference /path/to/gsm8k.jsonl
```

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

`0.6.4` — descripción de PyPI alineada con el wording de producto (señales de overlap).

**No en este release (a propósito):** matching semántico / paráfrasis, gates de CI, scans streaming multi-GB, detectores de provenance/licencia.

**Siguiente:** según uso real. Puente probable: códigos de salida para pipelines (`--fail-on-overlap`). El modelo de matching se mantiene estable salvo que haga falta.

## Qué no hace RupuData

- determinar propiedad legal ni certificar copyright
- garantizar que un dataset es legalmente seguro
- detectar toda forma de contaminación de benchmarks
- afirmar comprensión semántica de near-duplicates
- reemplazar scanners de licencia o frameworks a gran escala

## Contrato de auditoría técnica

Para quien necesita reproducir el hallazgo con exactitud. Los reportes JSON permiten auditar el método:

```text
input → configuration → method → result
```

### Modelo de matching (fuente → unit → spec)

| `method.unit` | Fuente de texto | Specs |
|---------------|-----------------|--------|
| `full_record` | registro completo | `record_exact_v1` / `record_normalized_v1` |
| `field_text` | `method.field` explícito (`--text-field`) | `text_exact_v1` / `text_normalized_v1` |
| `extracted_text` | `text_extraction` (p. ej. first_non_empty) | `text_exact_v1` / `text_normalized_v1` |

Las specs `text_*` definen cómo se hashea un texto plano. No definen de dónde salió ese texto — el comando declara la fuente.

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
