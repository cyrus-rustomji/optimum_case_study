"""12-month forward model of OP Mainnet net sequencer revenue (Q3: "how can we grow our take").

net revenue = [ base-load gas x price of blockspace  +  congestion (spike) premium ] x ETH/USD  x (1 - L1 cost ratio)

Why this shape: the decomposition (sql/02) shows revenue fell because the price of blockspace fell ~10x while gas
used stayed flat, and sql/09 shows ~1/3 of the year's revenue came from 10 congested days. So the model splits
revenue into the part OP can price (base load) and the part it cannot control (volatility spikes).

Levers (each is a separate, additive line so Finance can switch them on/off):
  A. Minimum base fee (Jovian `minBaseFee`, live since Dec 2025, set by the SystemConfig owner):
     raise the floor price of gas to F. Volume responds with a constant elasticity per segment:
     automated/bot traffic is price-sensitive (it is 86% of txs at ~$0.002/tx), user-facing apps much less.
  B. Payments BD: win K more card/payment issuers of ether.fi's scale (ether.fi moved ~70k cards to OP Mainnet
     in 2026). Each adds ether.fi's observed gas run-rate x an induced-activity multiplier (stablecoin transfers,
     swaps, bridging the issuer's users trigger).
  C. L1 data fee hygiene: since Oct 2025 users pay less L1 data fee than OP's L1 cost. Re-tune the blob/base fee
     scalars so the data leg at least breaks even.

All assumptions live in ASSUMPTIONS below; outputs go to outputs/tables/model_*.csv and outputs/model.json.
"""
import json
from dataclasses import asdict, dataclass, replace

import pandas as pd

from load import ROOT, TABLES, connect, run_sql


@dataclass(frozen=True)
class Scenario:
    name: str
    eth_usd: float                 # average ETH price over the next 12 months
    gas_growth: float              # organic change in base-load gas vs the last 90 days
    spike_multiple: float          # next 12m congestion premium as a multiple of the last 12m premium
    l1_cost_ratio: float           # L1 cost as % of gross
    floor_mwei: float              # lever A: minimum base fee (mwei per gas); 0 = lever off
    elasticity_bot: float          # lever A: % change in bot gas per % change in price
    elasticity_user: float         # lever A: same for user-facing traffic
    payments_wins: float           # lever B: ether.fi-scale payment issuers won in the year
    induced_multiple: float        # lever B: total gas per $ of issuer's own gas (1 = no knock-on activity)
    fix_l1_data_fee: bool          # lever C


def inputs(con):
    """Observed inputs, all from the pipeline tables (no hand-typed numbers)."""
    days = pd.read_csv(TABLES / "09_fee_concentration_by_day.csv", parse_dates=["date"])
    days["fee_eth"] = days.gas_used * days.mwei_per_gas * 1e-12
    p_med = days.mwei_per_gas.median()
    # base-load = what each day would have paid at no more than the median price; the rest is the spike premium
    days["base_eth"] = days.gas_used.clip(lower=0) * days.mwei_per_gas.clip(upper=p_med) * 1e-12
    days["spike_eth"] = days.fee_eth - days.base_eth
    spike_eth = days.spike_eth.sum()
    # the single biggest day (2025-10-10 liquidation cascade) is a tail event; base case excludes it
    spike_ex_top = days.sort_values("fee_eth", ascending=False).iloc[1:].spike_eth.sum()

    # natural experiment: prior period -> last 12m, blockspace price fell and volume rose (sql/02)
    dec = pd.read_csv(TABLES / "02_revenue_decomposition.csv")
    d = dec[dec.base_period.str.startswith("Prior")].iloc[0]
    import math
    ln_p = math.log(1 + d.pct_blockspace_price)
    obs_el_tx = math.log(1 + d.pct_tx_volume) / ln_p
    obs_el_gas = math.log((1 + d.pct_tx_volume) * (1 + d.pct_gas_per_tx)) / ln_p

    last90 = days[days.date > days.date.max() - pd.Timedelta(days=90)]
    seg = con.execute("""
        SELECT CASE WHEN d.segment IN ('unlabeled_bot', 'mev_bots') THEN 'bot' ELSE 'user' END AS seg,
               sum(c.gas_used) AS gas
        FROM contract_activity c JOIN address_dim d ON d.address = c.to_address
        WHERE c.date > DATE '2026-09-15' - INTERVAL 90 DAY
        GROUP BY 1""").df().set_index("seg").gas
    etherfi = con.execute("""
        SELECT sum(c.gas_used) / count(DISTINCT c.date) * 365 AS gas_yr
        FROM contract_activity c JOIN address_dim d ON d.address = c.to_address
        WHERE d.app = 'ether.fi' AND c.date > DATE '2026-09-15' - INTERVAL 90 DAY""").fetchone()[0]
    m = pd.read_csv(TABLES / "01_revenue_monthly.csv", parse_dates=["month"])
    recent = m[m.month >= "2025-10-01"]
    l1_gap_yr = (recent.l1_cost_usd.sum() - recent.l1_data_fee_usd.sum()) / len(recent) * 12
    eth_now = con.execute("SELECT avg(eth_price_usd) FROM eth_price WHERE date > DATE '2026-08-15'").fetchone()[0]
    h = json.loads((ROOT / "outputs" / "headline.json").read_text())
    return {
        "p_med_mwei": float(p_med),
        "p_med_90d_mwei": float(last90.mwei_per_gas.median()),
        "gas_yr_bot": float(seg["bot"] / 90 * 365),
        "gas_yr_user": float(seg["user"] / 90 * 365),
        "spike_eth_l12m": float(spike_eth),
        "spike_multiple_ex_top_day": float(spike_ex_top / spike_eth),
        "observed_elasticity_txs": float(obs_el_tx),
        "observed_elasticity_gas": float(obs_el_gas),
        "base_eth_l12m": float(days.base_eth.sum()),
        "etherfi_gas_yr": float(etherfi),
        "l1_data_gap_usd_yr": float(max(l1_gap_yr, 0)),
        "eth_usd_now": float(eth_now),
        "l1_ratio_llama": 1 - h["net_margin_l12m"],
        "l1_ratio_gtp": h["gtp_cost_overlap"] / h["gtp_gross_overlap"],
        "net_l12m_usd": h["net_l12m_usd"],
    }


def run(s: Scenario, x: dict) -> dict:
    p0 = x["p_med_90d_mwei"]
    gb, gu = x["gas_yr_bot"] * (1 + s.gas_growth), x["gas_yr_user"] * (1 + s.gas_growth)
    base_eth = (gb + gu) * p0 * 1e-12

    lever_a_eth = 0.0
    if s.floor_mwei > p0:
        r = s.floor_mwei / p0
        gb1, gu1 = gb * r ** s.elasticity_bot, gu * r ** s.elasticity_user
        lever_a_eth = (gb1 + gu1) * s.floor_mwei * 1e-12 - base_eth
        price = s.floor_mwei
    else:
        gb1, gu1, price = gb, gu, p0

    lever_b_eth = s.payments_wins * x["etherfi_gas_yr"] * s.induced_multiple * price * 1e-12
    spike_eth = x["spike_eth_l12m"] * s.spike_multiple

    keep = (1 - s.l1_cost_ratio) * s.eth_usd
    out = {
        "scenario": s.name,
        "baseline_usd": base_eth * keep,
        "spike_usd": spike_eth * keep,
        "lever_a_min_base_fee_usd": lever_a_eth * keep,
        "lever_b_payments_bd_usd": lever_b_eth * keep,
        "lever_c_l1_fee_fix_usd": x["l1_data_gap_usd_yr"] if s.fix_l1_data_fee else 0.0,
        "bot_gas_change": (gb1 / gb - 1) if gb else 0.0,
        "user_gas_change": (gu1 / gu - 1) if gu else 0.0,
        "price_mwei": price,
    }
    out["no_action_usd"] = out["baseline_usd"] + out["spike_usd"]
    out["total_usd"] = out["no_action_usd"] + out["lever_a_min_base_fee_usd"] + out["lever_b_payments_bd_usd"] \
        + out["lever_c_l1_fee_fix_usd"]
    out["uplift_vs_no_action"] = out["total_usd"] / out["no_action_usd"] - 1
    return out


def scenarios(x):
    base = Scenario("Base", eth_usd=x["eth_usd_now"], gas_growth=0.0,
                    spike_multiple=round(x["spike_multiple_ex_top_day"], 2),
                    l1_cost_ratio=x["l1_ratio_llama"], floor_mwei=2.5, elasticity_bot=-0.6, elasticity_user=-0.1,
                    payments_wins=2, induced_multiple=2.0, fix_l1_data_fee=True)
    bear = replace(base, name="Bear", eth_usd=x["eth_usd_now"] * 0.6, gas_growth=-0.2, spike_multiple=0.25,
                   l1_cost_ratio=x["l1_ratio_gtp"], elasticity_bot=-1.0, elasticity_user=-0.2, payments_wins=0,
                   induced_multiple=1.0)
    bull = replace(base, name="Bull", eth_usd=x["eth_usd_now"] * 1.4, gas_growth=0.2, spike_multiple=1.0,
                   floor_mwei=4.0, elasticity_bot=-0.4, elasticity_user=-0.05, payments_wins=4, induced_multiple=3.0)
    return base, bear, bull


TORNADO = [  # (label, field, low, high) - one variable at a time around Base
    ("ETH price -40% / +40%", "eth_usd", 0.6, 1.4),
    ("Congestion premium 0.25x / 1.0x of last year", "spike_multiple", None, None),
    ("Min base fee 1.5 / 4.0 mwei", "floor_mwei", None, None),
    ("Bot elasticity -1.2 / -0.3", "elasticity_bot", None, None),
    ("Organic gas -20% / +20%", "gas_growth", None, None),
    ("Payments wins 0 / 4", "payments_wins", None, None),
    ("L1 cost: growthepie / DefiLlama ratio", "l1_cost_ratio", None, None),
]
TORNADO_VALUES = {
    "spike_multiple": (0.25, 1.0), "floor_mwei": (1.5, 4.0), "elasticity_bot": (-1.2, -0.3),
    "gas_growth": (-0.2, 0.2), "payments_wins": (0, 4),
}


def main():
    con = connect()
    run_sql(con, "03_address_dim")
    x = inputs(con)
    base, bear, bull = scenarios(x)
    res = pd.DataFrame([run(s, x) for s in (bear, base, bull)])
    res.to_csv(TABLES / "model_scenarios.csv", index=False)
    pd.DataFrame([asdict(s) for s in (bear, base, bull)]).to_csv(TABLES / "model_assumptions.csv", index=False)

    b = run(base, x)["total_usd"]
    rows = []
    for label, field, lo, hi in TORNADO:
        if field == "eth_usd":
            vals = (base.eth_usd * lo, base.eth_usd * hi)
        elif field == "l1_cost_ratio":
            vals = (x["l1_ratio_gtp"], x["l1_ratio_llama"])
        else:
            vals = TORNADO_VALUES[field]
        lo_v, hi_v = (run(replace(base, **{field: v}), x)["total_usd"] for v in vals)
        rows.append({"driver": label, "low_usd": lo_v, "high_usd": hi_v, "base_usd": b, "swing": abs(hi_v - lo_v)})
    tor = pd.DataFrame(rows).sort_values("swing", ascending=False)
    tor.to_csv(TABLES / "model_tornado.csv", index=False)

    # floor sweep: what each minimum base fee level does to revenue and bot volume (Base elasticities)
    sweep = pd.DataFrame([{**run(replace(base, floor_mwei=f, payments_wins=0, fix_l1_data_fee=False), x), "floor": f}
                          for f in [0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0]])
    sweep.to_csv(TABLES / "model_floor_sweep.csv", index=False)

    (ROOT / "outputs" / "model.json").write_text(json.dumps({"inputs": x, "scenarios": res.to_dict("records")},
                                                            indent=2, default=float))
    pd.set_option("display.width", 220)
    print(json.dumps(x, indent=1))
    print(res.round(3).T.to_string())
    print(tor.round(0).to_string())
    print(sweep[["floor", "total_usd", "lever_a_min_base_fee_usd", "bot_gas_change", "user_gas_change"]].round(3).to_string())


if __name__ == "__main__":
    main()
