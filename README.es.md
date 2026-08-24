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

Prepará JSONL train/test de GSM8K (p. ej. Hugging Face `openai/gsm8k`) e inyectá tres preguntas del test en una copia del train:

```bash
head -n 3 gsm8k_test.jsonl > leak.jsonl
cat gsm8k_train.jsonl >> leak.jsonl

rupudata benchmark-check leak.jsonl \
  --benchmark gsm8k \
  --reference gsm8k_test.jsonl
```

Salida de terminal (paths abreviados):

```text
╭───────────────────────────────╮
│ RupuData v0.6.6               │
│ Follow the path of your data. │
╰───────────────────────────────╯

Benchmark check: …/leak.jsonl vs GSM8K

Benchmark
──────────────────────────────
  Benchmark                GSM8K
  Reference                user_reference
  Benchmark records        1,319
  Dataset rows             7,476
  Benchmark fingerprint    rupu:a75016197e210681

Overlap
──────────────────────────────
  Exact matches                  3
  Normalized matches             3
  Near matches                   n/a (disabled)
  Status                         OVERLAP_DETECTED
  Evidence pairs (exact)         3
  Evidence pairs (normalized)    3

Evidence (sample)
──────────────────────────────
  dataset_row    reference_row    field
  0              0                question
  1              1                question
  2              2                question
```

**3 overlaps exactos con el test set de GSM8K** bajo la metodología configurada.

RupuData reporta overlap textual. **No** determina por qué existe ni certifica que un modelo o dataset esté contaminado.

Train limpio vs test (sin leak):

```bash
rupudata compare gsm8k_train.jsonl gsm8k_test.jsonl --text-field question
rupudata benchmark-check gsm8k_train.jsonl --benchmark gsm8k --reference gsm8k_test.jsonl
```

→ overlap exacto/normalizado **0**, status **`NO_OVERLAP_DETECTED`**.

Scan sobre el train limpio:

```bash
rupudata scan gsm8k_train.jsonl
```

```text
Dataset
──────────────────────────────
  Rows           7,473
  Format         jsonl
  Size           1.79 MB
  Columns        question
  Fingerprint    rupu:fedca4cb0fa770fe

Duplicates
──────────────────────────────
  Exact duplicates    0
  Unique records      7,473
  Duplicate rate      0.00%
  Near-dupe pairs     2
  Records flagged     4
  Near-dupe rate      0.05%
  Near threshold      0.85
  Candidates          minhash_lsh
```

```text
7,476 training records (con 3 filas del test inyectadas)
        │
        ▼
     RupuData
        │
        ├── scan (train limpio): 0 exact duplicates, 2 near-dupe pairs
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

`0.6.6` — ejemplos del README alineados al output real de la CLI en corridas GSM8K.

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
