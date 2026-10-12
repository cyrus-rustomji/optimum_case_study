"""Static PNG charts for the deck. Every chart reads from outputs/tables (never re-computes numbers).

Style: one y-axis per chart (no dual axes), thin marks, recessive grid, fixed categorical order
(validated palette: dataviz skill reference palette, light mode, slots 1-5 pass CVD/normal-vision checks;
three slots sit below 3:1 contrast, so every series is also direct-labelled or legended).
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import pandas as pd  # noqa: E402

from load import CHARTS, L12M, ROOT, TABLES  # noqa: E402

SURFACE = "#fcfcfb"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
S = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
GRAY = "#b9b8b2"
SEG_ORDER = ["named_app", "unlabeled_multi", "long_tail", "mev_bots", "unlabeled_bot"]
SEG_LABEL = {"named_app": "Named apps & infra", "unlabeled_multi": "Unnamed multi-user contracts",
             "long_tail": "Long tail (small contracts)", "mev_bots": "Labelled MEV / trading bots",
             "unlabeled_bot": "Unnamed automated contracts (bots)"}
SEG_COLOR = dict(zip(SEG_ORDER, [S[0], S[2], GRAY, S[3], S[1]]))

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 12, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.titlesize": 14, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
    "legend.frameon": False, "legend.fontsize": 11, "text.parse_math": False,
})

usd = mtick.FuncFormatter(lambda v, _: f"${v / 1e9:.1f}B" if abs(v) >= 1e9 else f"${v / 1e6:.1f}M" if abs(v) >= 1e6 else f"${v / 1e3:.0f}k" if abs(v) >= 1e3 else f"${v:.0f}")
pct = mtick.PercentFormatter(1.0, decimals=0)
L0, L1 = pd.Timestamp(L12M[0]), pd.Timestamp(L12M[1])


def t(name, **kw):
    return pd.read_csv(TABLES / f"{name}.csv", **kw)


def save(fig, name):
    CHARTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHARTS / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def shade_window(ax):
    ax.axvspan(L0, L1, color="#f0efec", zorder=0, lw=0)
    ax.text(L0 + pd.Timedelta(days=8), 0.97, "last 12 months", transform=ax.get_xaxis_transform(), color=MUTED,
            fontsize=10, va="top")


def revenue_monthly():
    m = t("01_revenue_monthly", parse_dates=["month"])
    fig, ax = plt.subplots(figsize=(11, 4.8))
    shade_window(ax)
    w = 22
    ax.bar(m.month, m.execution_fee_usd, width=w, color=S[0], label="Execution fee (L2 gas)", zorder=2)
    ax.bar(m.month, m.l1_data_fee_usd, bottom=m.execution_fee_usd, width=w, color=S[3], label="L1 data fee charged to users",
           zorder=2, edgecolor=SURFACE, linewidth=1)
    ax.plot(m.month, m.l1_cost_usd, color=INK, lw=2, marker="o", ms=4, label="What OP paid Ethereum (L1 cost)", zorder=3)
    ax.yaxis.set_major_formatter(usd)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.set_title("Users' fees fell ~90% in 18 months; L1 cost is now a rounding error")
    ax.legend(loc="upper right")
    last = m.iloc[-2]
    ax.annotate(f"Aug 2026: ${last.gross_fee_usd / 1e3:.0f}k gross", (last.month, last.gross_fee_usd),
                xytext=(-10, 60), textcoords="offset points", ha="right", color=INK2, fontsize=11,
                arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.text(0, -0.2, "Sep 2026 is a partial month (to the 15th). L1 cost: DefiLlama op-mainnet fees − revenue.",
            transform=ax.transAxes, color=MUTED, fontsize=9)
    save(fig, "01_revenue_monthly")


def drivers_indexed():
    m = t("01_revenue_monthly", parse_dates=["month"])
    seg = t("05_segments_monthly", parse_dates=["month"]).groupby("month")[["gas_used", "fee_eth"]].sum()
    m = m.set_index("month").join(seg)
    m = m[m.index < "2026-09-01"]
    days = m.days
    series = {
        "Transactions / day": (m.fee_paying_txs / days, S[0]),
        "Daily active addresses": (m.avg_daily_active_addresses, S[2]),
        "ETH price": (m.avg_eth_price_usd, GRAY),
        "Price of blockspace (ETH per gas)": (m.fee_eth / m.gas_used, S[1]),
    }
    fig, ax = plt.subplots(figsize=(11, 4.8))
    for label, (s, c) in series.items():
        idx = s / s.iloc[0] * 100
        ax.plot(idx.index, idx, color=c, lw=2.2 if "blockspace" in label or "Trans" in label else 1.6)
        ax.text(idx.index[-1] + pd.Timedelta(days=6), idx.iloc[-1], f"{label}  {idx.iloc[-1]:.0f}", color=INK2,
                va="center", fontsize=11)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_yticks([5, 10, 25, 50, 100, 200, 400])
    ax.axhline(100, color=MUTED, lw=1, ls="--")
    ax.set_xlim(m.index[0] - pd.Timedelta(days=10), m.index[-1] + pd.Timedelta(days=150))
    ax.set_xticks([d for d in pd.date_range(m.index[0], m.index[-1], freq="3MS")])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    px = (m.fee_eth / m.gas_used)
    ax.set_title(f"More transactions, fewer people, blockspace ~{px.iloc[0] / px.iloc[-1]:.0f}× cheaper (Jan 2025 = 100, log scale)")
    save(fig, "02_drivers_indexed")


def decomposition():
    d = t("02_revenue_decomposition")
    r = d[d.base_period.str.startswith("Prior")].iloc[0]
    steps = [("Prior period\n(Jan–Sep 15 2025)", r.usd_per_day_base, "total"),
             (f"More txs\n{r.pct_tx_volume:+.0%}", r.effect_tx_volume, "d"),
             (f"Lighter txs\n(gas/tx {r.pct_gas_per_tx:+.0%})", r.effect_gas_per_tx, "d"),
             (f"Cheaper blockspace\n(ETH/gas {r.pct_blockspace_price:+.0%})", r.effect_blockspace_price, "d"),
             (f"ETH price\n{r.pct_eth_price:+.0%}", r.effect_eth_price, "d"),
             ("Last 12 months", r.usd_per_day_comp, "total")]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    run = 0
    for i, (lab, v, kind) in enumerate(steps):
        if kind == "total":
            ax.bar(i, v, color=INK2, width=0.6)
            run = v
            ax.text(i, v, f"${v / 1e3:.1f}k/day", ha="center", va="bottom", fontsize=12, color=INK, weight="bold")
        else:
            bottom = run if v >= 0 else run + v
            ax.bar(i, abs(v), bottom=bottom, color=S[2] if v >= 0 else S[1], width=0.6)
            ax.text(i, run + max(v, 0), f"{'+' if v >= 0 else '−'}${abs(v) / 1e3:.1f}k", ha="center", va="bottom",
                    fontsize=12, color=INK)
            run += v
    ax.set_xticks(range(len(steps)), [s[0] for s in steps], fontsize=11)
    ax.yaxis.set_major_formatter(usd)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Gross fees per day (USD)")
    ax.set_title("Revenue per day fell 70%: volume grew, but the price of blockspace collapsed")
    ax.text(0, -0.26, "Additive LMDI decomposition: revenue/day = txs/day × gas/tx × ETH per gas × USD per ETH; effects sum exactly to the change.",
            transform=ax.transAxes, color=MUTED, fontsize=9)
    save(fig, "03_decomposition")


def daily_spikes():
    d = t("09_fee_concentration_by_day", parse_dates=["date"]).sort_values("date")
    h = json.loads((ROOT / "outputs" / "headline.json").read_text())
    fig, ax = plt.subplots(figsize=(11, 4.6))
    top = d.nlargest(10, "total_fee_usd")
    ax.bar(d.date, d.total_fee_usd, width=1, color=GRAY)
    ax.bar(top.date, top.total_fee_usd, width=1.5, color=S[1])
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(usd)
    peak = d.loc[d.total_fee_usd.idxmax()]
    ax.annotate(f"{peak.date:%b %d %Y} (market crash): ${peak.total_fee_usd / 1e3:.0f}k in one day\n"
                f"= {peak.total_fee_usd / d.total_fee_usd.sum():.0%} of the year; blockspace price {peak.mwei_per_gas / d.mwei_per_gas.median():.0f}× median",
                (peak.date, peak.total_fee_usd), xytext=(25, -8), textcoords="offset points", fontsize=11, color=INK,
                va="top")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.set_title(f"The 10 busiest days (orange) earned {h['top10_days_share']:.0%} of the year's fees")
    ax.set_ylabel("Gross fees per day (log scale)")
    save(fig, "04_daily_spikes")


def segments():
    s = t("05_segments_monthly", parse_dates=["month"])
    p = s.pivot_table(index="month", columns="segment", values="fee_usd", aggfunc="sum")[SEG_ORDER]
    share = p.div(p.sum(axis=1), axis=0)
    a = t("04_app_ranking").groupby("segment")[["fee_usd", "txs"]].sum()
    a = a / a.sum()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.9), gridspec_kw={"width_ratios": [1.15, 1]})
    # left: share of fees vs share of txs, last 12m
    y = range(len(SEG_ORDER))
    ax1.barh([i + 0.2 for i in y], [a.loc[k, "fee_usd"] for k in SEG_ORDER], height=0.38,
             color=[SEG_COLOR[k] for k in SEG_ORDER])
    ax1.barh([i - 0.2 for i in y], [a.loc[k, "txs"] for k in SEG_ORDER], height=0.38, color="none",
             edgecolor=[SEG_COLOR[k] for k in SEG_ORDER], hatch="///", linewidth=1)
    for i, k in enumerate(SEG_ORDER):
        ax1.text(a.loc[k, "fee_usd"] + 0.01, i + 0.2, f"{a.loc[k, 'fee_usd']:.0%} of fees", va="center", fontsize=10, color=INK)
        ax1.text(a.loc[k, "txs"] + 0.01, i - 0.2, f"{a.loc[k, 'txs']:.0%} of txs", va="center", fontsize=10, color=INK2)
    ax1.set_yticks(list(y), [SEG_LABEL[k] for k in SEG_ORDER], fontsize=11)
    ax1.xaxis.set_major_formatter(pct)
    ax1.set_xlim(0, 1.05)
    ax1.grid(axis="y", visible=False)
    ax1.set_title("Last 12m: fees (solid) vs txs (hatched)", fontsize=12)
    # right: monthly fee share over time
    bottom = 0
    for k in SEG_ORDER:
        ax2.fill_between(share.index, bottom, bottom + share[k], color=SEG_COLOR[k], linewidth=0, step="mid")
        bottom = bottom + share[k]
    ax2.yaxis.set_major_formatter(pct)
    ax2.set_ylim(0, 1)
    ax2.set_xlim(share.index[0], share.index[-1])
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%y"))
    ax2.set_title("Monthly share of fees", fontsize=12)
    ax2.grid(False)
    fig.suptitle("Most of OP's revenue comes from bots, not from named apps", x=0.01, ha="left", fontsize=14,
                 weight="bold", color=INK)
    fig.tight_layout(w_pad=3)
    save(fig, "05_segments")


def top_customers():
    r = t("04_app_ranking").head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(11, 5.4))
    ax.barh(r.customer, r.fee_usd, color=[SEG_COLOR[s] for s in r.segment], height=0.65)
    for i, (_, row) in enumerate(r.iterrows()):
        ax.text(row.fee_usd + 2000, i, f"${row.fee_usd / 1e3:.0f}k · {row.share_of_gross:.1%} · ${row.usd_per_1k_tx:,.0f}/1k tx",
                va="center", fontsize=10, color=INK2)
    ax.xaxis.set_major_formatter(usd)
    ax.set_xlim(0, r.fee_usd.max() * 1.45)
    ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=SEG_COLOR[k]) for k in SEG_ORDER]
    ax.legend(handles, [SEG_LABEL[k] for k in SEG_ORDER], loc="lower right", fontsize=10)
    h = json.loads((ROOT / "outputs" / "headline.json").read_text())
    ax.set_title(f"Top 15 fee payers, last 12 months: top 10 = {h['top10_customer_share']:.0%} of fees, mostly bots")
    save(fig, "06_top_customers")


def apps_vs_op():
    a = t("07_apps_vs_op")
    a = a[a.has_tracked_contracts].head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(11, 5.4))
    y = range(len(a))
    ax.hlines(y, a.paid_op_usd, a.app_fees_usd, color=GRID, lw=3)
    ax.scatter(a.app_fees_usd, y, s=80, color=S[0], zorder=3, label="Fees users paid the app (DefiLlama)")
    ax.scatter(a.paid_op_usd, y, s=80, color=S[1], zorder=3, label="Gas those apps' contracts paid OP")
    for i, (_, row) in enumerate(a.iterrows()):
        ax.text(row.app_fees_usd * 1.25, i, f"{row.app_fees_per_1usd_gas:,.0f}×", va="center", fontsize=10, color=INK2)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(usd)
    ax.set_yticks(list(y), a.app, fontsize=11)
    ax.set_xlim(a.paid_op_usd.min() / 2, a.app_fees_usd.max() * 4)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=10)
    h = json.loads((ROOT / "outputs" / "headline.json").read_text())
    ax.set_title(f"Apps earned ${h['app_fees_l12m'] / 1e6:.0f}M in fees; OP's whole gross take was ${h['gross_l12m_usd'] / 1e6:.2f}M (log scale)")
    ax.text(0, -0.2, "× = app fees per $1 of gas paid to OP. Gas covers only contracts above file 06's size threshold, so it is a floor.",
            transform=ax.transAxes, color=MUTED, fontsize=9)
    save(fig, "07_apps_vs_op")


def ecosystem():
    e = t("08_ecosystem_quarterly", parse_dates=["qtr"])
    e["label"] = e.qtr.dt.year.astype(str).str[2:] + "Q" + e.qtr.dt.quarter.astype(str)
    panels = [
        ("Stablecoin supply (avg)", [("native_stable_supply_usd", "Native (e.g. USDC)", S[0]),
                                     ("bridged_stable_supply_usd", "Bridged (e.g. USDT)", S[3])]),
        ("Bridge flows per quarter", [("bridge_in_usd_91d", "Inbound", S[2]), ("bridge_out_usd_91d", "Outbound", S[1])]),
        ("DeFi TVL (avg)", [("tvl_usd", "TVL", S[0])]),
        ("New addresses per quarter", [("new_addresses_91d", "New addresses", S[0])]),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.8))
    for ax, (title, ser) in zip(axes, panels):
        for col, lab, c in ser:
            ax.plot(e.label, e[col], color=c, lw=2, marker="o", ms=4, label=lab)
        ax.set_title(title, fontsize=12)
        ax.yaxis.set_major_formatter(usd if "address" not in title else mtick.FuncFormatter(lambda v, _: f"{v / 1e6:.1f}M"))
        ax.tick_params(axis="x", labelsize=9, rotation=45)
        ax.set_ylim(bottom=0)
        if len(ser) > 1:
            ax.legend(fontsize=9, loc="lower left")
    fig.suptitle("Non-gas customers: liquidity and users are shrinking; bridging turned net-inbound after ether.fi (26Q2)",
                 x=0.01, ha="left", fontsize=13, weight="bold", color=INK)
    fig.tight_layout()
    save(fig, "08_ecosystem")


def scenarios():
    s = t("model_scenarios")
    h = json.loads((ROOT / "outputs" / "headline.json").read_text())
    parts = [("baseline_usd", "Base load at today's prices", S[0]), ("spike_usd", "Congestion premium", GRAY),
             ("lever_a_min_base_fee_usd", "A: minimum base fee", S[1]),
             ("lever_b_payments_bd_usd", "B: payments BD", S[2]), ("lever_c_l1_fee_fix_usd", "C: L1 data-fee fix", S[3])]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    x = ["Last 12 months\n(actual net)"] + [f"{n}\nnext 12 months" for n in s.scenario]
    ax.bar(0, h["net_l12m_usd"], color=INK2, width=0.55)
    ax.text(0, h["net_l12m_usd"], f"${h['net_l12m_usd'] / 1e6:.2f}M", ha="center", va="bottom", fontsize=12, weight="bold")
    for i, (_, row) in enumerate(s.iterrows(), start=1):
        b = 0
        for col, lab, c in parts:
            ax.bar(i, row[col], bottom=b, color=c, width=0.55, edgecolor=SURFACE, linewidth=1.5, label=lab if i == 1 else None)
            b += row[col]
        ax.text(i, b, f"${b / 1e6:.2f}M", ha="center", va="bottom", fontsize=12, weight="bold")
        ax.hlines(row.no_action_usd, i - 0.34, i - 0.28, color=INK, lw=1.5)
        ax.text(i - 0.36, row.no_action_usd, f"no action\n${row.no_action_usd / 1e6:.2f}M", fontsize=9, color=INK2, va="center", ha="right")
    ax.set_xticks(range(len(x)), x)
    ax.yaxis.set_major_formatter(usd)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", fontsize=10)
    ax.set_title("Net sequencer revenue, next 12 months: levers offset the drift and add upside")
    save(fig, "09_scenarios")


def tornado():
    d = t("model_tornado").iloc[::-1]
    base = d.base_usd.iloc[0]
    fig, ax = plt.subplots(figsize=(11, 4.6))
    for i, (_, r) in enumerate(d.iterrows()):
        lo, hi = min(r.low_usd, r.high_usd), max(r.low_usd, r.high_usd)
        ax.barh(i, base - lo, left=lo, color=S[1], height=0.55)
        ax.barh(i, hi - base, left=base, color=S[0], height=0.55)
        ax.text(lo, i, f"${lo / 1e6:.2f}M ", ha="right", va="center", fontsize=10, color=INK2)
        ax.text(hi, i, f" ${hi / 1e6:.2f}M", ha="left", va="center", fontsize=10, color=INK2)
    ax.axvline(base, color=INK, lw=1.2)
    ax.set_yticks(range(len(d)), d.driver, fontsize=11)
    ax.xaxis.set_major_formatter(usd)
    ax.set_xlim(d[["low_usd", "high_usd"]].min().min() * 0.8, d[["low_usd", "high_usd"]].max().max() * 1.12)
    ax.grid(axis="y", visible=False)
    ax.set_title(f"Base case ${base / 1e6:.2f}M: ETH price swings it most; the fee floor is the biggest lever we control")
    save(fig, "10_tornado")


def floor_sweep():
    f = t("model_floor_sweep")
    x = json.loads((ROOT / "outputs" / "model.json").read_text())["inputs"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.3))
    ax1.plot(f.floor, f.total_usd, color=S[0], lw=2, marker="o", ms=5)
    ax1.axvline(x["p_med_90d_mwei"], color=MUTED, ls="--", lw=1)
    ax1.text(x["p_med_90d_mwei"], ax1.get_ylim()[1], " today's median\n price", color=MUTED, fontsize=9, va="top")
    ax1.yaxis.set_major_formatter(usd)
    ax1.set_xlabel("Minimum base fee (mwei per gas)")
    ax1.set_title("Net revenue, next 12 months", fontsize=12)
    ax2.plot(f.floor, f.bot_gas_change, color=S[1], lw=2, marker="o", ms=5, label="Bot / automated gas")
    ax2.plot(f.floor, f.user_gas_change, color=S[2], lw=2, marker="o", ms=5, label="User-facing gas")
    ax2.yaxis.set_major_formatter(pct)
    ax2.set_xlabel("Minimum base fee (mwei per gas)")
    ax2.set_title("Volume lost (Base-case elasticities)", fontsize=12)
    ax2.legend(fontsize=10)
    fig.suptitle(f"A higher fee floor trades bot volume for revenue; a typical user tx at 2.5 mwei costs ${x['user_tx_cost_usd_at_2_5']:.4f}",
                 x=0.01, ha="left", fontsize=13, weight="bold", color=INK)
    fig.tight_layout()
    save(fig, "11_floor_sweep")


def retention():
    r = t("06_retention", parse_dates=["month"])
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.plot(r.month, r.logo_retention_3m, color=S[0], lw=2, marker="o", ms=5, label="Still paying 3 months later (count)")
    ax.plot(r.month, r.nrr_3m, color=S[1], lw=2, marker="o", ms=5, label="Fees 3 months later vs. cohort month (NRR)")
    ax.axhline(1, color=MUTED, ls="--", lw=1)
    ax.yaxis.set_major_formatter(pct)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.legend(fontsize=10, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2)
    ax.set_title("Paying customers churn fast: ~half are gone in 3 months and their spend shrinks")
    save(fig, "12_retention")


def main():
    for f in [revenue_monthly, drivers_indexed, decomposition, daily_spikes, segments, top_customers, apps_vs_op,
              ecosystem, scenarios, tornado, floor_sweep, retention]:
        f()
        print("chart:", f.__name__)


if __name__ == "__main__":
    main()
