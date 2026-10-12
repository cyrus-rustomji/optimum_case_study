"""Run every SQL step, save tidy tables to outputs/tables/, and write the headline numbers the deck quotes
to outputs/headline.json. Nothing in the deck is typed by hand: every figure is read from here.
"""
import json

import pandas as pd

from load import L12M, ROOT, connect, run_sql, save

STEPS = [
    "01_revenue_monthly",
    "02_revenue_decomposition",
    "03_address_dim",
    "04_app_ranking",
    "05_segments_monthly",
    "06_retention",
    "07_apps_vs_op",
    "08_ecosystem_quarterly",
    "09_fee_concentration_by_day",
]


def main():
    con = connect()
    t = {name: save(run_sql(con, name), name) for name in STEPS}
    save(con.execute("SELECT * FROM address_dim").df(), "address_dim")

    # last-12-month period totals straight from the daily tables (not from monthly rollups, which cut Sep in half)
    p = con.execute("""
        SELECT CASE WHEN f.date >= getvariable('l12m_start') THEN 'l12m' ELSE 'prior' END AS period,
               count(*) AS days, sum(f.total_fee_usd) AS gross, sum(f.execution_fee_usd) AS exec,
               sum(f.l1_data_fee_usd) AS l1_data_fee, sum(c.llama_l1_cost_usd) AS l1_cost,
               sum(c.gtp_l1_cost_usd) AS gtp_cost, sum(c.gtp_fees_usd) FILTER (WHERE c.gtp_l1_cost_usd IS NOT NULL) AS gtp_gross,
               sum(c.llama_l1_cost_usd) FILTER (WHERE c.gtp_l1_cost_usd IS NOT NULL) AS llama_cost_overlap,
               count(*) FILTER (WHERE c.gtp_l1_cost_usd IS NOT NULL) AS gtp_days,
               sum(f.fee_paying_txs) AS txs, sum(f.total_fee_eth) AS gross_eth, avg(f.eth_price_usd) AS eth_px
        FROM fees f LEFT JOIN l1_costs c USING (date) GROUP BY 1""").df().set_index("period")
    l, pr = p.loc["l12m"], p.loc["prior"]

    seg = (t["04_app_ranking"].groupby("segment")[["fee_usd", "txs"]].sum()
           .assign(fee_share=lambda d: d.fee_usd / d.fee_usd.sum(), tx_share=lambda d: d.txs / d.txs.sum()))
    rank = t["04_app_ranking"]
    apps = t["07_apps_vs_op"]
    days = t["09_fee_concentration_by_day"]
    eco = t["08_ecosystem_quarterly"]
    m = t["01_revenue_monthly"]
    ret = t["06_retention"]
    dec = t["02_revenue_decomposition"].set_index("base_period")

    run3 = m[(m.month >= pd.Timestamp("2026-06-01")) & (m.month <= pd.Timestamp("2026-08-01"))]
    h = {
        "window": {"l12m": L12M, "prior_days": int(pr.days), "l12m_days": int(l.days)},
        "gross_l12m_usd": l.gross, "net_l12m_usd": l.gross - l.l1_cost, "l1_cost_l12m_usd": l.l1_cost,
        "net_margin_l12m": 1 - l.l1_cost / l.gross,
        "exec_share_l12m": l.exec / l.gross,
        "l1_data_fee_l12m_usd": l.l1_data_fee,
        "gross_per_day_l12m": l.gross / l.days, "gross_per_day_prior": pr.gross / pr.days,
        "net_per_day_prior": (pr.gross - pr.l1_cost) / pr.days, "net_per_day_l12m": (l.gross - l.l1_cost) / l.days,
        "txs_per_day_l12m": l.txs / l.days, "txs_per_day_prior": pr.txs / pr.days,
        "usd_per_tx_l12m": l.gross / l.txs, "usd_per_tx_prior": pr.gross / pr.txs,
        "gross_eth_l12m": l.gross_eth, "avg_eth_px_l12m": l.eth_px,
        "gtp_overlap_days": int(l.gtp_days), "gtp_cost_overlap": l.gtp_cost, "llama_cost_overlap": l.llama_cost_overlap,
        "gtp_gross_overlap": l.gtp_gross,
        "run_rate_3m_gross_monthly": run3.gross_fee_usd.mean(), "run_rate_3m_net_monthly": run3.net_usd.mean(),
        "jan25_gross": float(m.loc[m.month == pd.Timestamp("2025-01-01"), "gross_fee_usd"].iloc[0]),
        "segments": seg.to_dict(orient="index"),
        "top10_customer_share": float(rank.cum_share.iloc[9]), "top50_customer_share": float(rank.cum_share.iloc[49]),
        "n_customers": int(len(rank)),
        "hhi_customers": float(((rank.share_of_gross * 100) ** 2).sum()),
        "top10_bots": int((rank.head(10).segment.isin(["unlabeled_bot", "mev_bots"])).sum()),
        "app_fees_l12m": apps.app_fees_usd.sum(), "app_revenue_l12m": apps.app_revenue_usd.sum(),
        "apps_paid_op_tracked": apps.paid_op_usd.sum(),
        "etherfi": apps[apps.app == "ether.fi"].iloc[0][["app_fees_usd", "app_revenue_usd", "paid_op_usd", "txs"]].to_dict(),
        "top_day": days.iloc[0][["date", "total_fee_usd", "cum_share", "mwei_per_gas"]].astype(str).to_dict(),
        "top10_days_share": float(days.cum_share.iloc[9]),
        "top5pct_days_share": float(days.cum_share.iloc[int(len(days) * 0.05) - 1]),
        "median_mwei_per_gas": float(days.median_mwei_per_gas.iloc[0]),
        "gas_l12m": float(days.gas_used.sum()),
        "retention_logo_3m_avg_l12m": float(ret[ret.month >= pd.Timestamp("2025-09-01")].logo_retention_3m.mean()),
        "retention_nrr_3m_avg_l12m": float(ret[ret.month >= pd.Timestamp("2025-09-01")].nrr_3m.mean()),
        "decomp_full": dec.iloc[0].to_dict() if len(dec) else {},
        "decomp_summer": dec.loc["Summer 2025 (Jun-Aug)"].to_dict(),
        "decomp_l12m_vs_prior": dec.loc["Prior: Jan 1 - Sep 15 2025"].to_dict(),
        "eco_first_q": eco.iloc[0].to_dict(), "eco_last_q": eco.iloc[-1].to_dict(),
        "eco_q3_2025": eco[eco.qtr == pd.Timestamp("2025-07-01")].iloc[0].to_dict(),
    }
    out = ROOT / "outputs" / "headline.json"
    out.write_text(json.dumps(h, indent=2, default=str))
    print(json.dumps({k: v for k, v in h.items() if not isinstance(v, dict)}, indent=1, default=str))


if __name__ == "__main__":
    main()
