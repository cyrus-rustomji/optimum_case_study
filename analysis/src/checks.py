"""Data-integrity checks. Run before trusting any number; the pipeline stops if one fails.

Each check prints PASS/FAIL with the measured value so the result can be pasted into the README / appendix.
"""
import sys

import pandas as pd

from load import TABLES, connect, run_sql

TOL = 0.001  # 0.1%


def checks(con):
    q = lambda s: con.execute(s).fetchone()  # noqa: E731
    out = []

    def add(name, ok, value):
        out.append({"check": name, "result": "PASS" if ok else "FAIL", "value": value})

    # 1. file 06 rows sum to file 01 daily totals (README promise; our customer shares depend on it)
    dev_fee, dev_tx = q("""
        WITH a AS (SELECT date, sum(total_fee_eth) f, sum(txs) t FROM contract_activity GROUP BY 1)
        SELECT max(abs(a.f / f.total_fee_eth - 1)), max(abs(a.t::DOUBLE / f.fee_paying_txs - 1))
        FROM a JOIN fees f USING (date)""")
    add("06 fees reconcile to 01 (max daily deviation)", dev_fee < TOL, f"{dev_fee:.5%}")
    add("06 txs reconcile to 01 (max daily deviation)", dev_tx < TOL, f"{dev_tx:.5%}")

    # 2. USD = ETH x price in file 01
    dev_usd = q("SELECT max(abs(total_fee_usd / (total_fee_eth * eth_price_usd) - 1)) FROM fees WHERE total_fee_eth > 0")[0]
    add("01 USD = ETH x price", dev_usd < TOL, f"{dev_usd:.6%}")
    dev_px = q("SELECT max(abs(f.eth_price_usd / p.eth_price_usd - 1)) FROM fees f JOIN eth_price p USING (date)")[0]
    add("01 price matches 02", dev_px < TOL, f"{dev_px:.6%}")

    # 3. execution + L1 data = total
    dev_sum = q("SELECT max(abs(execution_fee_eth + l1_data_fee_eth - total_fee_eth)) FROM fees")[0]
    add("01 execution + L1 data = total (ETH)", dev_sum < 1e-5, f"{dev_sum:.2e} ETH")

    # 4. no duplicate (date, address) and one row per day
    dups = q("SELECT count(*) - count(DISTINCT (date, to_address)) FROM contract_activity")[0]
    add("06 unique (date, to_address)", dups == 0, dups)
    n_days, n_dist, d0, d1 = q("SELECT count(*), count(DISTINCT date), min(date), max(date) FROM fees")
    add("01 one row per day, no gaps", n_days == n_dist == (d1 - d0).days + 1, f"{n_days} days {d0}..{d1}")

    # 5. the analysis window is exactly 365 days
    w = q("SELECT count(*) FROM fees WHERE date BETWEEN getvariable('l12m_start') AND getvariable('l12m_end')")[0]
    add("last-12-month window = 365 days", w == 365, w)

    # 6. labels cover every tracked address exactly once
    lab = q("SELECT count(*), count(DISTINCT address) FROM labels")
    tracked = q("SELECT count(DISTINCT to_address) FROM contract_activity WHERE to_address <> 'other'")[0]
    add("07 labels: one row per tracked address", lab[0] == lab[1] == tracked, f"{lab[0]} labels / {tracked} addresses")

    # 7. segmentation is exhaustive (every fee dollar lands in a segment)
    run_sql(con, "03_address_dim")
    seg_tot, all_tot = q("""SELECT (SELECT sum(c.total_fee_usd) FROM contract_activity c JOIN address_dim d
                                    ON d.address = c.to_address),
                                   (SELECT sum(total_fee_usd) FROM contract_activity)""")
    add("segments cover 100% of fees", abs(seg_tot / all_tot - 1) < 1e-9, f"{seg_tot / all_tot:.6%}")

    # 8. external L1 cost: complete for the window and cross-source agreement on gross
    miss = q("""SELECT count(*) FROM fees f LEFT JOIN l1_costs c USING (date)
                WHERE c.llama_l1_cost_usd IS NULL AND f.date >= DATE '2025-01-01'""")[0]
    add("L1 cost series has no missing days", miss == 0, miss)
    g = q("""SELECT sum(c.llama_fees_usd) / sum(f.total_fee_usd) FROM fees f JOIN l1_costs c USING (date)
             WHERE f.date BETWEEN getvariable('l12m_start') AND getvariable('l12m_end')""")[0]
    add("DefiLlama gross vs file 01 gross (last 12m)", abs(g - 1) < 0.05, f"{g - 1:+.2%}")
    neg = q("SELECT count(*) FROM l1_costs WHERE llama_l1_cost_usd < 0")[0]
    add("no negative L1 cost days", neg == 0, neg)
    return pd.DataFrame(out)


def main():
    res = checks(connect())
    TABLES.mkdir(parents=True, exist_ok=True)
    res.to_csv(TABLES / "checks.csv", index=False)
    print(res.to_string(index=False))
    if (res.result == "FAIL").any():
        sys.exit("data checks failed")


if __name__ == "__main__":
    main()
