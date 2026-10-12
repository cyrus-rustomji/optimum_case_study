---
name: pipeline-perf-and-nondeterminism
description: OP case-study pipeline is CSV-parse bound (fixed via .cache parquet in load.py); its outputs are NOT run-to-run deterministic, so equivalence diffs need canonicalisation
metadata:
  type: project
---

As of 2026-10-12, runtime was dominated by DuckDB sniffing and parsing the raw CSVs on every query and in every
process. A Parquet copy cache in `load.py` took the pipeline from 3.4 s to 0.8 s. After that, all 9 SQL steps
together take about 60 ms, so SQL rewrites are not worth it.

**Why:** a naive byte diff of `outputs/` fails even on the unmodified pipeline. The outputs vary between runs
because of `address_dim.csv` row order (no ORDER BY), the order of the 23 zero-fee tied rows in
`04_app_ranking`, the token order from `07` `string_agg`, and last-bit float noise.

**How to apply:** for any future equivalence check, compare old against new on a frozen copy of the code with
only the changed file swapped, because other agents edit `src/` concurrently. Canonicalise only those known cases
and validate the comparator with a negative control.
