# OP Mainnet: who makes money, what's our share, how do we grow it

BI Lead take-home (OP Labs). The deliverable is `deck/OP_Mainnet_Revenue_BI_Lead.pptx` (24 slides).
The pipeline in this repo produces every number in the deck. No figure in the deck was typed in by hand.

## The answer in three lines
1. **Our share is about $1.2M a year and shrinking.** Net sequencer revenue over the last 12 months (2025-09-16 → 2026-09-15) was
   $1.22M, a 97% margin after L1 costs. The current run-rate is about $50k a month, against $680k in Jan 2025.
   Volume grew by 71% per day. The price of blockspace fell by 76%.
2. **Apps make the money.** They earned $41M in fees (DefiLlama), about 33× OP's gross take; ether.fi alone earned $18.5M while
   its contracts paid OP $10k in gas. Most of OP's revenue (about two-thirds) is paid by bots, and a third of it arrived on 10 volatile days.
3. **Grow the take by pricing blockspace.** Use a staged minimum base fee (Jovian `minBaseFee`), grow payments and stablecoin flow,
   and re-tune the L1 data-fee scalars. Base case for the next 12 months: $1.19M with these levers vs $0.90M without them
   (Bear $0.40M, Bull $3.09M).

## Run it
```bash
./run_all.sh              # checks → SQL → model → charts → deck  (~3 s; uses cached external data)
./run_all.sh --refetch    # also re-download the DefiLlama / growthepie L1 cost data
```
Requires Python 3.9+. The script creates `.venv` from `requirements.txt` (pandas, duckdb, matplotlib, python-pptx).
Raw data is read in place from `../Business Intelligence Lead Take-Home/case_study_data/csv/` and is never modified.

## Layout
| Path | What |
|---|---|
| `sql/01..09_*.sql` | DuckDB SQL, one file per analysis step, run directly on the CSVs. Each file's header says what it answers and why. |
| `src/load.py` | Paths, the analysis window, CSV → DuckDB views, `run_sql()` |
| `src/checks.py` | 13 integrity checks. The build stops on any FAIL. Results are saved to `outputs/tables/checks.csv` |
| `src/analysis.py` | Runs every SQL step and writes `outputs/tables/*.csv` + `outputs/headline.json` |
| `src/growth_model.py` | 12-month model: scenarios, tornado, fee-floor sweep. All assumptions live in one dataclass |
| `src/charts.py` | PNG charts, read from the output tables only |
| `src/build_deck.py` | Builds the .pptx from the charts, tables and the reviewed copy |
| `src/verify_copy.py` | Checks every number in the AI-drafted copy against the findings brief |
| `external/fetch_l1_costs.py` | Public L1 cost data: DefiLlama (primary), growthepie (check), on-chain via Blockscout (attempted) |
| `outputs/findings_brief.md` | Every key number with its definition. The single source handed to the copywriting agent |
| `outputs/agent_reports/` | Reports from the two AI agents (see below) |

## Metric definitions (and why these)
- **Gross sequencer revenue** = execution fee + L1 data fee paid by users (file 01). This is what OP bills.
- **L1 cost** = what OP pays Ethereum for batch posting. The files provided don't include it, so it comes from **DefiLlama
  op-mainnet `dailyFees − dailyRevenue`**. DefiLlama's gross agrees with file 01 within 3.4% over the last 12 months.
  Cross-check: growthepie `costs_total_usd` (its public file keeps only ~90 days). It puts cost at 5.6% of gross vs 2.1% from
  DefiLlama over the same 64 days. The model uses growthepie's ratio in the Bear case.
- **Net sequencer revenue ("our share")** = gross − L1 cost.
- **Price of blockspace** = ETH fees ÷ L2 gas used. This is the unit price OP's revenue depends on. It is what collapsed.
- **Decomposition**: revenue/day = txs/day × gas/tx × ETH per gas × USD per ETH. An additive LMDI split makes the four
  effects sum exactly to the change.
- **Customer** = the destination address of a transaction (file 06), grouped into apps through the labels in file 07.
  The precedence rule is in `sql/03_address_dim.sql`.
  **Bot** = an unnamed contract with ≤5 distinct senders per day, or ≥50 txs per sender-day. The median named app is 4.5 txs per sender-day.
- **Retention**: addresses paying ≥$10 in month m. Logo retention = the share still paying at m+3; NRR = their fees at m+3 ÷ their fees at m.

## Assumptions log
| # | Assumption | Why | Where |
|---|---|---|---|
| 1 | Last 12 months = 2025-09-16 → 2026-09-15; the prior period (258 days) is compared per day | Data starts 2025-01-01 | `load.py` |
| 2 | DefiLlama is the primary L1 cost source; growthepie is the high case | Only source covering the full window | `01_revenue_monthly.sql` |
| 3 | Fees belong to the destination contract | Only attribution file 06 allows | `03_address_dim.sql` |
| 4 | Dune `owner` = 'sushiswap' / 'Gnosis Safe' is ignored as an app name | Attached to unrelated contracts (Multicall3, LayerZero Executor, Squid) | `03_address_dim.sql` |
| 5 | Congestion premium = fees above the median day's price; Base case = last year excluding the 2025-10-10 crash day (0.67×) | A crash day is a tail event, not a plan | `growth_model.py` |
| 6 | Bot elasticity −0.6, user elasticity −0.1 | Observed response to the 76% price cut was −0.38 (txs) / −0.08 (gas). The chosen values are deliberately more elastic | `growth_model.py` |
| 7 | Payment wins scale like ether.fi's last-90-day gas, ×2 induced activity | ether.fi is the only observed payments migration | `growth_model.py` |
| 8 | ETH price = average of the last 30 days, ±40% for Bear/Bull | Price is outside our control and drives USD revenue | `growth_model.py` |

## Known limitations
- Labels cover about 340 of 1,082 addresses, so "bot" is inferred from behaviour, not identity.
- File 06 has a size threshold, so gas paid by apps is a floor.
- File 08 USD values are at DefiLlama's prices; file 01 uses Allium's median ETH price.
- OP Mainnet's current `minBaseFee` value was not verified on-chain. Check the SystemConfig before acting on lever A.
- The on-chain L1 cost rebuild (`external/fetch_l1_costs.py`) works, but Blockscout's keyless tier rate-limited it (HTTP 429).
  With an Etherscan/Blockscout API key it would give a third, fully independent L1 cost series.

## AI usage & verification
Claude Code (Opus) did the analysis interactively. Here is where AI was used, and how its output was checked:
| Where | How it was checked |
|---|---|
| Writing SQL / Python | Every result comes from code. `checks.py` runs 13 assertions on each build: file 06 reconciles to file 01 (max 0.012%/day on fees, exact on txs), USD = ETH × price, no gaps or duplicates, segments cover 100% of fees, and the external gross agrees within 5% |
| Label → app mapping | Top 150 labelled addresses reviewed by eye. Mis-attributions found and handled (Dune owner noise, rule 4) |
| Bot heuristic | Fee-weighted distribution of txs per sender-day by segment inspected before choosing the thresholds (median named app 4.5, median bot 636) |
| External data | DefiLlama vs file 01 gross (−3.4%), DefiLlama vs growthepie L1 cost over 64 overlapping days |
| Public facts (Jovian min base fee, Base leaving the Superchain, buyback) | Read from primary or secondary sources (Optimism docs/specs, DL News), and cited on the slides they support |
| **verified-performance-optimizer** agent | Profiled the pipeline and found that ~90% of the time went to DuckDB re-parsing the CSVs. It added a Parquet cache in `load.py` (rebuilt automatically when a CSV changes): the pipeline went from 3.4 s to 0.8 s (4.3×), and peak memory fell by about 30%. Equivalence was proven by diffing every table against frozen A/B baselines (rtol 1e-9; 13/13 checks still pass) and by confirming the diff harness catches injected errors. Along the way it found **run-to-run non-determinism** (unordered ties in rankings, unordered `string_agg`, an arbitrary category pick). These were then fixed with explicit tiebreakers, and two consecutive builds now produce identical rows and order (floats within 1e-12). Report: `outputs/agent_reports/optimizer_report.md` |
| **metrics-to-business-translator** agent | Drafted the slide copy, recommendations, KPI tree, and risks from `findings_brief.md` only (`outputs/agent_reports/deck_copy.json`). `src/verify_copy.py` checked all 293 numeric tokens against the brief: 1 was not verbatim ("96 to 97 cents", derived from the 96.8% margin, which is fine). On human review, one over-general claim was tightened (Base = ~90% of Collective inflows *in Jan 2026*). The agent also flagged a real bug: a `decomp_full` key that duplicated another comparison. It was removed |
| Charts | Each PNG opened and checked for label collisions, wrong scales and misleading encodings. There are no dual axes, and categorical colours are validated for colour-blind safety |
