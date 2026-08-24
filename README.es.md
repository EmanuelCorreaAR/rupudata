# RupuData

**Idioma:** [English](README.md) | [Español](README.es.md)

**Follow the path of your data.**

RupuData responde una pregunta incómoda: **¿mi training data solapa los datos con los que evalúo el modelo?**

CLI local para **duplicados**, **overlap train/eval** y **señales de overlap con benchmarks**, con reportes JSON deterministas. **Señales técnicas, no certificación legal.**

## Instalación

Requiere **Python 3.9+**.

```bash
pip install rupudata
rupudata --help
```

## Inicio rápido

```bash
rupudata scan dataset.jsonl
rupudata compare train.jsonl eval.jsonl
rupudata compare train.jsonl eval.jsonl --text-field question
rupudata benchmark-check train.jsonl --benchmark gsm8k
```

`compare` por defecto usa **registros completos**. Usá `--text-field` cuando solo una columna deba participar del matching.

## Ejemplo real (GSM8K)

Exportá train/test desde Hugging Face (`openai/gsm8k`) a JSONL. Cada línea se ve así:

```json
{"question": "Natalia sold clips to 48 of her friends in April…", "answer": "72"}
```

```bash
pip install datasets
python - <<'PY'
from datasets import load_dataset
import json

def write_jsonl(path, split, key="question"):
    rows = load_dataset("openai/gsm8k", "main", split=split)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps({key: row[key]}, ensure_ascii=False) + "\n")
    print(split, len(rows), "->", path)

write_jsonl("gsm8k_train.jsonl", "train")
write_jsonl("gsm8k_test.jsonl", "test")
PY
```

### Camino A — inyectar tres preguntas del test (overlap)

```bash
head -n 3 gsm8k_test.jsonl > leak.jsonl
cat gsm8k_train.jsonl >> leak.jsonl

rupudata benchmark-check leak.jsonl \
  --benchmark gsm8k \
  --reference gsm8k_test.jsonl
```

```text
╭───────────────────────────────╮
│ RupuData v0.7.0               │
│ Follow the path of your data. │
╰───────────────────────────────╯

Benchmark check: leak.jsonl vs GSM8K

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

### Camino B — train limpio (sin leak)

```bash
rupudata compare gsm8k_train.jsonl gsm8k_test.jsonl --text-field question
rupudata benchmark-check gsm8k_train.jsonl --benchmark gsm8k --reference gsm8k_test.jsonl
rupudata scan gsm8k_train.jsonl
```

→ compare / benchmark-check: **0** overlaps, **`NO_OVERLAP_DETECTED`**.

→ scan (7.473 filas): **0** duplicados exactos; **2** pares near-dupe léxicos. Evidencia JSON:

```json
"near_duplicates": {
  "pairs": 2,
  "records_flagged": 4,
  "evidence": [
    { "left": 1174, "right": 7233, "jaccard": 0.8688, "field": "question" },
    { "left": 2483, "right": 6691, "jaccard": 0.9262, "field": "question" }
  ],
  "evidence_truncated": false
}
```

| Filas | Jaccard | Qué cambia |
|------|---------|------------|
| `1174` ↔ `7233` | 0.87 | Misma plantilla “Martha / butterflies”; totales y color preguntado distintos |
| `2483` ↔ `6691` | 0.93 | Mismo problema del regalo / cassettes / auriculares; solo el nombre (`Josie` → `Amanda`) |

```text
Record 2483
  Josie received $50 as a gift. She plans to buy two cassette tapes…

Record 6691
  Amanda received $50 as a gift. She plans to buy two cassette tapes…

Similarity (Jaccard on character shingles): 0.93
```

Eso es near-duplicación **léxica**. RupuData **no** afirma que sean el mismo problema para un alumno, ni plagio — solo que los strings comparten suficientes shingles bajo el umbral configurado.

### Reference de benchmark: sample demo vs auditoría real

> **Advertencia:** Sin `--reference`, el default `gsm8k` usa un **sample empaquetado diminuto**. Un `NO_OVERLAP_DETECTED` contra ese sample **no** significa que tu dataset esté libre de GSM8K. Para una auditoría real, pasá el export con `--reference`.

```bash
rupudata benchmark-check train.jsonl --benchmark gsm8k --reference /path/to/gsm8k.jsonl
```

## Probar los ejemplos del repo

```bash
git clone https://github.com/EmanuelCorreaAR/rupudata.git
cd rupudata
pip install -e .
```

```bash
rupudata compare examples/train.jsonl examples/eval.jsonl
rupudata benchmark-check examples/train_with_gsm8k_overlap.jsonl --benchmark gsm8k
rupudata scan examples/near_dupes.jsonl --near-duplicate-threshold 0.85
```

## Estado

`0.7.1` — README más corto; la metodología de auditoría vive en `docs/AUDIT.md`.

**No en este release (a propósito):** matching semántico / paráfrasis, gates de CI, scans streaming multi-GB, detectores de provenance/licencia.

**Siguiente:** según uso real (probable `--fail-on-overlap` para CI).

## Desarrollo

```bash
git clone https://github.com/EmanuelCorreaAR/rupudata.git
cd rupudata
pip install -e ".[dev]"
pytest
python -m build
```

## Contrato de auditoría técnica

Metodología, units y formas de evidencia: **[docs/AUDIT.md](docs/AUDIT.md)**.

## Licencia

Apache License 2.0
