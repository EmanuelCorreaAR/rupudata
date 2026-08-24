# RupuData

**Idioma:** [English](README.md) | [Español](README.es.md)

**Follow the path of your data.**

RupuData responde una pregunta incómoda: **¿mi training data solapa los datos con los que evalúo el modelo?**

Detecta **duplicados**, **overlap train/eval** y **señales de overlap con benchmarks** — en local, con reportes de auditoría deterministas y legibles por máquina. Señales técnicas, no certificación legal.

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

## Ejemplo real (GSM8K)

Contra el split **test** completo de GSM8K como `--reference` (1.319 preguntas), un train de 7.476 filas con tres preguntas del test inyectadas reporta:

```bash
rupudata benchmark-check leak.jsonl \
  --benchmark gsm8k \
  --reference gsm8k_test.jsonl
```

```text
RupuData v0.6.5

Dataset:       7,476 records
Reference:     GSM8K test — 1,319 records (user_reference)

Exact matches:       3
Normalized matches:  3
Near matches:        0

Status: OVERLAP_DETECTED

Evidence
  dataset_row  reference_row  field
  0            0              question
  1            1              question
  2            2              question
```

**3 overlaps exactos con el test set de GSM8K** bajo la metodología configurada.

RupuData reporta overlap textual. **No** determina por qué existe ni certifica que un modelo o dataset esté contaminado.

Sobre el split **train** limpio de GSM8K (7.473 registros):

```bash
rupudata scan gsm8k_train.jsonl
```

→ sin duplicados exactos; solo **2** pares near-duplicate léxicos (Jaccard ≥ 0.85, MinHash/LSH).

```text
7,476 training records
        │
        ▼
     RupuData
        │
        ├── scan: 0 exact duplicates, 2 near-dupe pairs
        │
        ▼
   GSM8K test (1,319) vía --reference
        │
        ▼
   3 exact overlaps → OVERLAP_DETECTED
```

### Reference de benchmark: sample demo vs auditoría real

> **Advertencia:** Sin `--reference`, el default `gsm8k` usa un **sample empaquetado diminuto**. Un `NO_OVERLAP_DETECTED` contra ese sample **no** significa que tu dataset esté libre de GSM8K. Para una auditoría real, pasá el export con `--reference`.

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

`0.6.5` — notes contextuales de benchmark + demo real GSM8K en el README.

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
