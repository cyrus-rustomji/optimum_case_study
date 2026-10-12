# Pipeline performance review (verified-performance-optimizer)

Date: 2026-10-12. Environment: `.venv` with pandas 2.3, DuckDB 1.4.5, on macOS.
Scope: `src/load.py`, `sql/01..09`, `src/checks.py`, `src/analysis.py`, `src/growth_model.py`. I did not read for
changes or touch `charts.py`, `build_deck.py` or `verify_copy.py`. Nothing was committed.

## TL;DR

* **One change applied:** `load.connect()` now registers each raw CSV as a view over a Parquet copy. The copy is
  written once by the *same* `read_csv_auto(..., header=true)` call, so type sniffing is unchanged. It is cached in
  `.cache/` and rebuilt automatically when a CSV's size or mtime, or the DuckDB version, changes.
* **Pipeline (checks + analysis + model): 3.41 s -> 0.80 s (4.3x). Full `./run_all.sh`: 5.10 s -> 2.46 s (2.1x).**
  The remaining full-run time is mostly `charts.py`, which is not mine.
* **Equivalence:** every CSV in `outputs/tables/` plus `headline.json` and `model.json` is identical (same columns,
  same row order, numeric rtol 1e-9). This held across 9 old x new pairings in a frozen A/B, including a cold-cache
  run, and across 5 real-tree `run_all.sh` runs. `checks.py` still prints **13 PASS**.
* **Found along the way:** the *baseline itself is not deterministic*. Four sources are listed below; none were
  fixed, all are reported.

## 1. Baseline profile (before any edit)

Wall-clock times, medians of 5 runs, using the original `load.py` on the current code:

| Step | Median |
|---|---|
| `checks.py` | 1.09 s |
| `analysis.py` | 1.48 s |
| `growth_model.py` | 0.84 s |
| `charts.py` (other agent) | 1.36 s |
| `build_deck.py` (other agent) | 0.35 s |
| full `./run_all.sh` | 5.10 s |

Inside one process, with the original `load.py`:

| Item | Time | Note |
|---|---|---|
| Python + pandas + duckdb import | 0.14-0.18 s | fixed cost per process, paid 3x |
| `connect()` | **0.38 s** | `CREATE VIEW ... read_csv_auto` *binds*, so it sniffs all 14 CSVs at connect time, in every process |
| one scan of `contract_activity` (208k rows) | 0.06 s | re-parsed by **every** query that touches it: 5x in checks, 7x in analysis, 4x in growth_model |
| `08_ecosystem_quarterly` | 0.31 s | re-parses 8 CSVs (stables twice, fees twice) |
| other SQL steps | 0.04-0.09 s each | almost entirely CSV parsing |

**Bottleneck:** CSV sniffing and parsing, repeated per query and per process. The cost is O(Q x N) parse work for
Q queries over N raw rows, against O(N) once. The SQL itself is cheap: after the fix, all 9 steps take **60 ms
in total**.

## 2. Change applied

### `src/load.py`: persisted Parquet copies of the raw CSVs
* `_parquet_copy(con, csv)` writes `COPY (SELECT * FROM read_csv_auto('<csv>', header=true)) TO '.cache/<stem>.<size>-<mtime_ns>-duckdb<version>.parquet'`.
  The SQL inside the `COPY` is exactly the expression the views used before, so DuckDB's sniffer makes the same
  type decisions.
* The view is then `CREATE VIEW <name> AS SELECT * FROM read_parquet('<that file>')`. View names, column names,
  types and row order are unchanged, so no SQL file or script had to change.
* The cache key lives in the file name: CSV size + mtime_ns + DuckDB version. Changing a CSV, or upgrading DuckDB
  (which can change the sniffer), forces a fresh sniff. The stale copy for that CSV is deleted.
* The write is atomic: it goes to `<name>.<pid>.tmp` and then `os.replace`. Other agents run these scripts
  concurrently, so a reader never sees a half-written file.
* `l1_costs` is **unchanged**. It is a 624-row file with an explicit schema, and `--refetch` regenerates it.
* Cost: about 15 MB on disk in `.cache/`. A cold first run builds the cache and is still faster than before
  (pipeline 1.30 s cold vs 3.41 s before).

### `.gitignore`: added `.cache/`
This keeps the 15 MB of derived Parquet out of git.

### Why Parquet over the alternatives (measured, pipeline = checks + analysis + model, medians of 5)

| Variant | checks | analysis | model | pipeline |
|---|---|---|---|---|
| original (views over CSV) | 1.087 | 1.461 | 0.818 | 3.366 s |
| in-process `CREATE TABLE` for all 14 | 0.741 | 0.790 | 0.741 | 2.272 s |
| hybrid: tables for contract_activity/fees/labels, views for the rest | 0.632 | 0.988 | 0.600 | 2.220 s |
| **Parquet cache (applied)** | 0.246 | 0.287 | 0.213 | **0.746 s** |

In-process tables still sniff and parse all 14 files in each of the 3 processes, about 0.55 s per process. The
cache pays that cost once. A single `.duckdb` file was rejected because DuckDB takes a file lock, and that lock
would collide with other agents running the scripts at the same time. Per-file Parquet has no locking problem.

## 3. Before / after

The comparison is an interleaved A/B in a sandbox. The code is identical and only `load.py` differs: 6 rounds,
round 1 discarded as warm-up, so n=5 per variant.

| Metric | Original | Optimized | Speedup |
|---|---|---|---|
| `checks.py` | 1.093 s | 0.261 s | 4.2x |
| `analysis.py` | 1.482 s | 0.304 s | 4.9x |
| `growth_model.py` | 0.838 s | 0.230 s | 3.6x |
| **pipeline (3 steps above)** | **3.41 s** | **0.80 s** | **4.3x** |
| `charts.py` (not mine) | 1.358 s | 1.353 s | 1.0x |
| `build_deck.py` (not mine) | 0.349 s | 0.349 s | 1.0x |
| **full `./run_all.sh`** | **5.10 s** | **2.46 s** | **2.1x** |
| cold first run, pipeline | 3.41 s | 1.30 s | 2.6x |
| peak RSS: checks / analysis / model | 205 / 398 / 179 MB | 160 / 267 / 131 MB | 1.3-1.5x less |
| Complexity | O(Q x N) CSV parse per process | O(N) once, then columnar scans | |

The real tree after the change (`./run_all.sh`, medians of 5) matched: full 2.52 s, checks 0.27 s, analysis
0.32 s, model 0.24 s. One "old" A/B round hit a single 397 s `charts.py` stall, a matplotlib or system hiccup that
has nothing to do with this change. The medians are unaffected; the ranges excluding that round are tight (± 2%).

## 4. Equivalence evidence

### 4a. The baseline is not deterministic, so the diff must allow for that and nothing more
I ran the **unmodified** pipeline 5 times. The runs disagreed with each other and with the committed outputs:

| File | What varies run to run | Cause (in the original code) |
|---|---|---|
| `address_dim.csv` | row order (all 1083 rows; same set) | `analysis.py` saves `SELECT * FROM address_dim` with no ORDER BY |
| `04_app_ranking.csv` | order and `rank` of the last 23 rows | 23 customers tie at `fee_usd = 0`; `ORDER BY fee_usd DESC` and `row_number()` have no tiebreaker |
| `07_apps_vs_op.csv` | `defillama_protocols` token order (`socket-protocol, bungee`) | `string_agg(DISTINCT ...)` without ORDER BY |
| 02 / 05 / 06 / 08, `headline.json` | last-bit float differences | parallel aggregation sums in a different order; < 1e-12 relative |

The comparator (`diff_outputs.py`, in the scratchpad) compares strictly: same file set, same columns in the same
order, same shape and dtypes, row by row, non-numeric values exact, numeric `np.isclose(rtol=1e-9, atol=0,
equal_nan=True)`, and the JSON files recursively with the same key order. It canonicalises **only** the three
row-order cases above:
* `address_dim.csv` is sorted by its unique key `address`.
* `04_app_ranking.csv`: the `rank` column must be identical, and rows *not* in an exact `fee_usd` tie must sit in
  identical positions. Only rows inside a tie are re-sorted by customer.
* `07_apps_vs_op.csv`: the protocol tokens inside the one `defillama_protocols` cell are sorted.

**Validation of the comparator:**
* It passes all 5 unmodified runs against the baseline.
* A negative control injected four faults: a 1e-6 relative change in `01.net_usd`, a swap of two top-5 rows in
  04, one segment change in `address_dim`, and one category change in 07. It **flagged all 4**.

### 4b. Frozen A/B (same code, only `load.py` differs)

```
bash ab.sh        # 3 runs of checks.py -> analysis.py -> growth_model.py per variant, new run 1 from an empty cache
for i in 1 2 3; do for j in 1 2 3; do python diff_outputs.py ab_old/$i ab_new/$j; done; done
```
Result: **9/9 pairings `VERIFIED: All outputs identical`.** That covers all 15 CSVs, `headline.json` and
`model.json`. The 9 pairings include the cold-cache run.

### 4c. Source-level identity
For all 15 registered sources, `DESCRIBE` (column names and types) via Parquet == via `read_csv_auto`. Every row
fetched in file order is identical, with NaN-aware comparison. Row counts were 623 / 623 / 623 / 623 / 623 /
208718 / 1082 / 92441 / 11580 / 7346 / 185098 / 23607 / 204471 / 91973 / 623.
Result: `ALL SOURCES IDENTICAL (schema + every row, same order)`. This matters because 07's `any_value(category)`
depends on scan order, as described in section 6.

### 4d. Real working tree
```
rm -rf .cache && ./run_all.sh            # cold cache; 13 PASS printed by checks.py
python diff_outputs.py ab_old/1 after_real     -> VERIFIED: All outputs identical
python diff_outputs.py baseline after_real     -> only diff: headline.json key 'decomp_full' missing
bench.sh after 5   + diff_outputs.py ab_old/1 runs_after/{1..5} -> 5/5 VERIFIED
```
The `decomp_full` difference against the pre-edit snapshot comes from the lead's concurrent edit to
`src/analysis.py` at 11:23, which removed that key. It is not caused by this change; on the same code the outputs
are identical. Every CSV and `model.json` also match the pre-edit snapshot.

Cache invalidation test on a scratch CSV: editing the file (`2` -> `2.5`) triggered a re-sniff (BIGINT -> DOUBLE),
removed the stale copy and left no temp files.

Note: `git status` shows `outputs/tables/*.csv` and the JSON files as modified. That is the baseline
nondeterminism from re-running the pipeline (section 4a), not a content change.

## 5. Considered and rejected / recommended but not applied

| Candidate | Measured after the fix | Decision |
|---|---|---|
| Rewrite `sql/04_app_ranking.sql` (two passes over `w` plus a window) | 16 ms | **Rejected.** About 0.6% of runtime, and a rewrite risks semantics such as RANGE-frame ties in `cum_share` |
| Rewrite `sql/03_address_dim.sql` | 4 ms | **Rejected.** Same reasoning |
| Rewrite `sql/09_fee_concentration_by_day.sql` | 1.6 ms | **Rejected.** Same reasoning |
| `growth_model.py` re-running `03_address_dim` / re-querying data | about 4 ms + 3 small queries | **Rejected.** It is negligible now, and re-deriving keeps the model independent of `analysis.py`'s side effects |
| Single Python process for checks + analysis + model | would save about 0.3-0.4 s of interpreter/pandas import (about 15% of the new full run) | **Recommended, not applied.** It changes `run_all.sh` structure, and other agents rely on the per-script entry points |
| In-process `CREATE TABLE` | 2.27 s vs 0.75 s with the cache | Rejected in favour of the cache (section 2) |
| Single `.duckdb` cache file | n/a | Rejected because of cross-process file-lock conflicts with concurrent agents |
| `SET threads=1` to remove float last-bit churn | would slow queries | **Not applied.** Differences are < 1e-12 relative; fix by rounding at save time if byte-stable CSVs are wanted |

## 6. Correctness issues noticed in the SQL / scripts (reported, NOT fixed)

1. **`04_app_ranking`: nondeterministic order and `rank` for ties.** `row_number() OVER (ORDER BY c.fee_usd DESC)`
   and the final `ORDER BY` have no tiebreaker. Today only the 23 zero-fee customers tie, so the headline numbers
   (`cum_share.iloc[9]` / `iloc[49]`) are safe. A tie inside the top 50 would make them run-dependent. Suggested
   fix: `ORDER BY c.fee_usd DESC, c.customer` in both places.
   Also, `sum(...) OVER (ORDER BY fee_usd DESC)` uses the default RANGE frame, so tied rows share a `cum_share`.
   That is probably intended, but worth knowing.
2. **`07_apps_vs_op`: `any_value(f.category)` is arbitrary for 8 apps** that have two categories in the window:
   uniswap (dexs / developer-tools), chamber, ether.fi (crypto-card-issuer / lending), circle, moonwell, curve,
   extra and sushiswap. The category shown depends on scan order. It was stable in every run here, but nothing
   guarantees it. Suggest picking the fee-weighted top category, or `string_agg(DISTINCT category ORDER BY category)`.
3. **`07_apps_vs_op`: `string_agg(DISTINCT f.protocol, ', ')` has no ORDER BY**, so the token order varies between
   runs (`bungee` / `socket-protocol`). Suggest `string_agg(DISTINCT f.protocol, ', ' ORDER BY f.protocol)`.
4. **`analysis.py` saves `address_dim.csv` without ORDER BY.** All 1083 rows reshuffle on every run, which creates
   noisy diffs. Suggest `SELECT * FROM address_dim ORDER BY address`.
5. **`04` `any_value(segment)` per customer** is safe today, because no app spans more than one segment. If a
   named app ever had both a `trading`-labelled address (mev_bots) and a normal one (named_app), its segment would
   become arbitrary. A one-line check in `checks.py` would guard it.
6. **`09`: `row_number()` has no tiebreaker** either. There are no fee ties today, so the issue is latent.
7. **`01_revenue_monthly`: `fees JOIN activity` is an inner join.** A day missing from file 03 would silently drop
   that day's fees from the monthly totals. Both files have 623 rows today, but `checks.py` only verifies
   completeness for `fees`.
8. **Hard-coded window end in `growth_model.py`.** The 90-day queries use `DATE '2026-09-15'` directly instead of
   `L12M[1]` from `load.py`, and so does the new `user_gas_per_tx` query. It is correct today, but it duplicates
   the window constant that `load.py` exists to centralise.

## Files changed
* `src/load.py`: `_parquet_copy()` helper, `CACHE` path, and views now read Parquet. `l1_costs` is unchanged.
* `.gitignore`: added `.cache/`.

Verification artefacts are in the session scratchpad: `diff_outputs.py`, `bench.sh`, `ab.sh`, `bench_ab.tsv`,
`baseline/`, `ab_old/`, `ab_new/`, `runs_after/`.
