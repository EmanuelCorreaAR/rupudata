# Contrato técnico de auditoría

**Idioma:** [English](AUDIT.md) | [Español](AUDIT.es.md)

Los reportes JSON de RupuData siguen:

```text
input → configuration → method → result
```

Son **señales técnicas, no certificación legal.**

Archivos por defecto: `rupudata-report.json`, `rupudata-compare.json`, `rupudata-benchmark.json`.

## Modelo de matching (fuente → unit → spec)

| `method.unit` | Fuente de texto | Specs |
|---------------|-----------------|--------|
| `full_record` | registro completo | `record_exact_v1` / `record_normalized_v1` |
| `field_text` | campo explícito `method.field` (`--text-field`) | `text_exact_v1` / `text_normalized_v1` |
| `extracted_text` | `text_extraction` (p. ej. first_non_empty) | `text_exact_v1` / `text_normalized_v1` |

Las specs `text_*` definen **cómo** se hashea un texto plano. **No** definen de dónde salió ese texto: eso lo declara el comando.

## Vocabulario por comando

| Comando | Campo | Spec / unit |
|---------|--------|-------------|
| `scan` | `exact_duplicates` | `record_normalized_v1` (`unit=full_record`) |
| `compare` | `exact_overlap` / `normalized_overlap` | `record_*` o `text_*` según `method.unit` |
| `benchmark-check` | `exact` / `normalized` | `text_*` con `unit=extracted_text` |

### Evidencia en `compare`

- `matches.exact`: solo pares de filas (+ `field` en modo field_text). Sin `also_exact` ni diffs.
- `matches.normalized`: siempre trae `also_exact`. Si es `false`, full_record agrega `differing_fields` y field_text agrega `difference`; si es `true`, se omiten los diffs.

### Evidencia de near-duplicates en `scan` (0.7.0+)

`result.near_duplicates` incluye:

- `pairs`, `records_flagged`, `record_rate`
- `evidence[]`: `{ left, right, jaccard, field? }` (filas 0-based; `field` cuando hay una sola fuente de texto)
- `evidence_truncated`: `true` si hay más pares que `--max-evidence`

La evidencia documenta el **hallazgo** (qué filas, qué score). **No** embebe el texto completo del registro: abrí el dataset en esos índices para inspeccionar.

## Qué significa “normalized” (fingerprint + duplicados exactos de `scan`)

Policy id: `record_normalized_v1`.

| Paso | Comportamiento |
|---|---|
| Campos | **Todos** los del registro |
| Keys | Ordenadas en forma recursiva |
| Strings | Solo `str.strip()` |
| Espacios internos | **Se conservan** |
| Mayúsculas / Unicode | Sin lowercasing, sin NFC/NFKC |
| Hash | SHA-256 sobre JSON compacto ordenado |

Fingerprint = SHA-256 del **multiset ordenado** de hashes por registro → `rupu:` + 16 hex.

Los near-duplicates usan **otra** prep de texto (`near_text_v1`: minúsculas + colapsar whitespace sobre el texto comparable). Solo similitud léxica — no paráfrasis.

```bash
rupudata scan dataset.parquet --skip-near-duplicates
```
