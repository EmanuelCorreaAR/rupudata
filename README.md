# RupuData

**Follow the path of your data.**

RupuData answers an uncomfortable question: **does my training data overlap with data I use to evaluate my model?**

Local CLI for **duplicates**, **train/eval overlap**, and **benchmark overlap signals**, with deterministic JSON reports. **Technical signals, not legal certification.**

## Install

Requires **Python 3.9+**.

```bash
pip install rupudata
rupudata --help
```

## Quick start

```bash
rupudata scan dataset.jsonl
rupudata compare train.jsonl eval.jsonl
rupudata compare train.jsonl eval.jsonl --text-field question
rupudata compare train.jsonl eval.jsonl --fail-on-overlap
rupudata compare train.jsonl eval.jsonl --max-overlap-rate 0.001
rupudata scan train.jsonl --max-duplicate-rate 0 --max-near-duplicate-rate 0.01
rupudata benchmark-check train.jsonl --benchmark gsm8k
rupudata benchmark-check train.jsonl --benchmark gsm8k --fail-on-overlap
```

`compare` defaults to **full records**. Use `--text-field` when only one column should participate in matching.

Policy gates (`--fail-on-overlap`, `--max-*-rate`) exit **2** when thresholds are exceeded. Exit **1** is reserved for errors. The JSON report (including `gate`) is written either way.

## Real-world example (GSM8K)

Export train/test from Hugging Face (`openai/gsm8k`) to JSONL. Each line looks like:

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

### Path A — inject three test questions (overlap)

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

**3 exact GSM8K test-set overlaps detected** under the configured matching methodology.

### Path B — clean train (no leak)

```bash
rupudata compare gsm8k_train.jsonl gsm8k_test.jsonl --text-field question
rupudata benchmark-check gsm8k_train.jsonl --benchmark gsm8k --reference gsm8k_test.jsonl
rupudata scan gsm8k_train.jsonl
```

→ compare / benchmark-check: **0** overlaps, **`NO_OVERLAP_DETECTED`**.

→ scan (7,473 rows): **0** exact duplicates; **2** lexical near-dupe pairs. JSON evidence:

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

| Rows | Jaccard | What differs |
|------|---------|----------------|
| `1174` ↔ `7233` | 0.87 | Same “Martha / butterflies” template; different totals and which color is asked |
| `2483` ↔ `6691` | 0.93 | Same gift / cassette / headphone word problem; only the name (`Josie` → `Amanda`) |

```text
Record 2483
  Josie received $50 as a gift. She plans to buy two cassette tapes…

Record 6691
  Amanda received $50 as a gift. She plans to buy two cassette tapes…

Similarity (Jaccard on character shingles): 0.93
```

That is **lexical** near-duplication. RupuData does **not** claim the questions are the same math problem for a student, nor plagiarism — only that the strings share enough character shingles under the configured threshold.

### Benchmark reference: demo sample vs real audit

> **Warning:** Without `--reference`, default `gsm8k` uses a **tiny packaged sample**. A `NO_OVERLAP_DETECTED` against that sample does **not** mean your dataset is free of GSM8K. For an actual audit, pass the real export with `--reference`.

```bash
rupudata benchmark-check train.jsonl --benchmark gsm8k --reference /path/to/gsm8k.jsonl
```

## Try the packaged examples

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

## Status

`0.9.0` — quality policy gates (`--max-*-rate`) + explicit rates; optional `gate` in the audit JSON.

**Not in this release (on purpose):** semantic / paraphrase matching, streaming multi-GB scans, provenance/license detectors.

**Next:** stabilize the audit contract toward 1.0.

## Development

```bash
git clone https://github.com/EmanuelCorreaAR/rupudata.git
cd rupudata
pip install -e ".[dev]"
pytest
python -m build
```

## Technical audit contract

Methodology, matching units, and evidence shapes: **[docs/AUDIT.md](docs/AUDIT.md)**.

## License

Apache License 2.0
