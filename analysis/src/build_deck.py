"""Build deck/OP_Mainnet_Revenue_BI_Lead.pptx from:
  outputs/agent_reports/deck_copy.json   - slide copy (drafted by the metrics-to-business-translator agent,
                                           reviewed against the numbers by src/verify_copy.py)
  outputs/charts/*.png                   - charts (src/charts.py)
  outputs/tables/*.csv                   - tables for scenario, KPI and check slides
"""
import json

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from load import CHARTS, ROOT, TABLES

COPY = json.loads((ROOT / "outputs" / "agent_reports" / "deck_copy.json").read_text())
H = json.loads((ROOT / "outputs" / "headline.json").read_text())
OUT = ROOT / "deck" / "OP_Mainnet_Revenue_BI_Lead.pptx"

RED = RGBColor(0xFF, 0x04, 0x20)        # OP-style accent, used sparingly (rules, numbers)
INK = RGBColor(0x0B, 0x0B, 0x0B)
INK2 = RGBColor(0x52, 0x51, 0x4E)
MUTED = RGBColor(0x8A, 0x89, 0x84)
PANEL = RGBColor(0xF3, 0xF2, 0xEF)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BG = RGBColor(0xFC, 0xFC, 0xFB)
FONT = "Helvetica Neue"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
W, HGT = prs.slide_width, prs.slide_height
page = {"n": 0}


def new_slide(section=None):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    page["n"] += 1
    if page["n"] > 1:
        text(s, f"{page['n']}", Inches(12.6), Inches(7.05), Inches(0.5), Inches(0.3), 10, MUTED, align=PP_ALIGN.RIGHT)
        text(s, "OP Mainnet revenue · BI Lead case study", Inches(0.6), Inches(7.05), Inches(6), Inches(0.3), 10, MUTED)
    if section:
        text(s, section.upper(), Inches(0.6), Inches(0.35), Inches(8), Inches(0.3), 11, RED, bold=True)
    return s


def text(slide, s, x, y, w, h, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Emu(0)
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = s
    r.font.size, r.font.bold, r.font.name = Pt(size), bold, FONT
    r.font.color.rgb = color
    return tb


def bullets(slide, items, x, y, w, h, size=15, color=INK, gap=8):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(0)
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        r = p.add_run()
        r.text = "▪  " + it
        r.font.size, r.font.name = Pt(size), FONT
        r.font.color.rgb = color
    return tb


def panel(slide, x, y, w, h, fill=PANEL):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def headline(slide, s, size=28):
    text(slide, s, Inches(0.6), Inches(0.65), Inches(12.1), Inches(1.0), size, INK, bold=True)


def chart_slide(section, key, chart, side=True):
    c = COPY["slides"][key]
    s = new_slide(section)
    headline(s, c["headline"])
    img = CHARTS / f"{chart}.png"
    if side:
        pic = s.shapes.add_picture(str(img), Inches(0.6), Inches(1.75), width=Inches(8.4))
        if pic.height > Inches(5.1):
            ratio = Inches(5.1) / pic.height
            pic.height, pic.width = Inches(5.1), int(pic.width * ratio)
        panel(s, Inches(9.25), Inches(1.75), Inches(3.5), Inches(5.0))
        bullets(s, c["bullets"], Inches(9.45), Inches(1.95), Inches(3.1), Inches(4.7), size=14)
    else:
        pic = s.shapes.add_picture(str(img), Inches(0.6), Inches(1.65), width=Inches(12.1))
        if pic.height > Inches(3.9):
            ratio = Inches(3.9) / pic.height
            pic.height, pic.width = Inches(3.9), int(pic.width * ratio)
        bullets(s, c["bullets"], Inches(0.6), Inches(5.7), Inches(12.1), Inches(1.3), size=13, gap=3)
    return s


def table(slide, df, x, y, w, col_w=None, size=11, header_fill=INK, row_h=0.32):
    rows, cols = df.shape[0] + 1, df.shape[1]
    t = slide.shapes.add_table(rows, cols, x, y, w, Inches(row_h * rows)).table
    for j, c in enumerate(df.columns):
        if col_w:
            t.columns[j].width = Inches(col_w[j])
        cell = t.cell(0, j)
        cell.text = str(c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = header_fill
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.size, r.font.bold, r.font.name = Pt(size), True, FONT
                r.font.color.rgb = WHITE
    for i, row in enumerate(df.itertuples(index=False), start=1):
        for j, v in enumerate(row):
            cell = t.cell(i, j)
            cell.text = str(v)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if i % 2 else PANEL
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size, r.font.name = Pt(size), FONT
                    r.font.color.rgb = INK
    return t


def m(v):
    return f"${v / 1e6:.2f}M"


# ---------------------------------------------------------------- 1. title
s = new_slide()
panel(s, 0, 0, Inches(0.25), HGT, fill=RED)
text(s, COPY["title"], Inches(0.9), Inches(2.0), Inches(11.5), Inches(1.6), 44, INK, bold=True)
text(s, COPY["subtitle"], Inches(0.9), Inches(3.6), Inches(11.5), Inches(0.8), 20, INK2)
text(s, COPY["answer_one_liner"], Inches(0.9), Inches(4.7), Inches(11.0), Inches(1.2), 18, INK)
text(s, "Business Intelligence Lead take-home · data through 2026-09-15 · code & SQL in the accompanying git repo",
     Inches(0.9), Inches(6.6), Inches(11.5), Inches(0.4), 12, MUTED)

# ---------------------------------------------------------------- 2. exec summary
e = COPY["exec_summary"]
s = new_slide("Executive summary")
headline(s, COPY.get("exec_headline", "Apps make the money; OP keeps ~$1.2M, mostly from bots. Price blockspace to grow it."), size=26)
tiles = [("Net sequencer revenue, last 12m", m(H["net_l12m_usd"]), f"{H['net_margin_l12m']:.0%} margin after L1 costs"),
         ("Fees apps earned, last 12m", f"${H['app_fees_l12m'] / 1e6:.0f}M", f"≈{H['app_fees_l12m'] / H['gross_l12m_usd']:.0f}× OP's gross take"),
         ("Share of fees paid by bots", f"{H['segments']['unlabeled_bot']['fee_share'] + H['segments']['mev_bots']['fee_share']:.0%}",
          f"{H['segments']['unlabeled_bot']['tx_share'] + H['segments']['mev_bots']['tx_share']:.0%} of transactions"),
         ("Next 12m, Base case with levers", m(json.loads((ROOT / 'outputs' / 'model.json').read_text())['scenarios'][1]['total_usd']),
          f"vs {m(json.loads((ROOT / 'outputs' / 'model.json').read_text())['scenarios'][1]['no_action_usd'])} with no action")]
for i, (lab, val, sub) in enumerate(tiles):
    x = Inches(0.6 + i * 3.08)
    panel(s, x, Inches(1.8), Inches(2.9), Inches(1.55))
    text(s, lab, x + Inches(0.15), Inches(1.9), Inches(2.6), Inches(0.4), 12, INK2)
    text(s, val, x + Inches(0.15), Inches(2.25), Inches(2.6), Inches(0.6), 30, RED, bold=True)
    text(s, sub, x + Inches(0.15), Inches(2.9), Inches(2.6), Inches(0.4), 11, INK2)
text(s, "Finding & evidence", Inches(0.6), Inches(3.55), Inches(6), Inches(0.3), 14, INK, bold=True)
bullets(s, [e["finding"]] + e["evidence"], Inches(0.6), Inches(3.9), Inches(6.1), Inches(3.0), size=12, gap=4)
text(s, "So what", Inches(7.0), Inches(3.55), Inches(5.7), Inches(0.3), 14, INK, bold=True)
text(s, e["implication"], Inches(7.0), Inches(3.9), Inches(5.7), Inches(1.3), 13, INK)
text(s, "Recommended action", Inches(7.0), Inches(5.2), Inches(5.7), Inches(0.3), 14, RED, bold=True)
text(s, e["action"], Inches(7.0), Inches(5.55), Inches(5.7), Inches(1.3), 13, INK)

# ---------------------------------------------------------------- 3. approach
c = COPY["slides"]["approach"]
s = new_slide("Approach")
headline(s, c["headline"])
bullets(s, c["bullets"], Inches(0.6), Inches(1.8), Inches(6.2), Inches(4.8), size=15)
chk = pd.read_csv(TABLES / "checks.csv")
panel(s, Inches(7.2), Inches(1.8), Inches(5.5), Inches(4.9))
text(s, f"Data checks run on every build: {(chk.result == 'PASS').sum()}/{len(chk)} pass", Inches(7.4), Inches(1.95),
     Inches(5.1), Inches(0.4), 14, INK, bold=True)
bullets(s, [f"{r.check}: {r.value}" for r in chk.itertuples()][:9], Inches(7.4), Inches(2.4), Inches(5.1), Inches(4.2), size=11, gap=3)

# ---------------------------------------------------------------- Q1 diagnosis
chart_slide("1 · Diagnose the revenue", "revenue_trend", "01_revenue_monthly")
chart_slide("1 · Diagnose the revenue", "decomposition", "03_decomposition")
s = chart_slide("1 · Diagnose the revenue", "spikes", "04_daily_spikes")
chart_slide("1 · Who is making money", "who_makes_money", "07_apps_vs_op")
# ---------------------------------------------------------------- Q2 customers
chart_slide("2 · Identify the customers", "segments", "05_segments", side=False)
chart_slide("2 · Identify the customers", "top_customers", "06_top_customers")
chart_slide("2 · Identify the customers", "retention", "12_retention")
chart_slide("2 · Other customer targets", "other_targets", "08_ecosystem", side=False)

# ---------------------------------------------------------------- Q3 recommendations
for r in COPY["recommendations"]:
    s = new_slide("3 · Recommendation")
    headline(s, r["name"], size=26)
    grid = [("Finding", r["finding"]), ("Evidence", r["evidence"]), ("Business implication", r["implication"]),
            ("Recommended action", r["action"])]
    for i, (lab, body) in enumerate(grid):
        x, y = Inches(0.6 + (i % 2) * 6.1), Inches(1.6 + (i // 2) * 1.6)
        panel(s, x, y, Inches(5.95), Inches(1.48))
        text(s, lab, x + Inches(0.2), y + Inches(0.1), Inches(5.5), Inches(0.3), 13, RED if i == 3 else INK2, bold=True)
        text(s, body, x + Inches(0.2), y + Inches(0.42), Inches(5.55), Inches(1.0), 12, INK)
    meta = [("Owner", r["owner"]), ("Timeline", r["timeline"]), ("Expected impact", r["expected_impact"]),
            ("Track", " · ".join(r["kpis"]))]
    for j, (lab, body) in enumerate(meta):
        y = Inches(4.9 + j * 0.5)
        text(s, lab, Inches(0.6), y, Inches(1.8), Inches(0.45), 12, INK2, bold=True)
        text(s, body, Inches(2.4), y, Inches(10.3), Inches(0.45), 11, INK)

chart_slide("3 · Business case", "scenarios", "09_scenarios")
s = chart_slide("3 · Business case", "sensitivity", "10_tornado", side=False)
chart_slide("3 · Business case", "floor_tradeoff", "11_floor_sweep", side=False)

# assumptions table
a = pd.read_csv(TABLES / "model_assumptions.csv").set_index("name").T
labels = {"eth_usd": "ETH price (avg, USD)", "gas_growth": "Organic gas change", "spike_multiple": "Congestion premium vs last 12m",
          "l1_cost_ratio": "L1 cost, % of gross", "floor_mwei": "Lever A: minimum base fee (mwei/gas)",
          "elasticity_bot": "Lever A: bot price elasticity", "elasticity_user": "Lever A: user price elasticity",
          "payments_wins": "Lever B: ether.fi-scale payment wins", "induced_multiple": "Lever B: induced-activity multiple",
          "fix_l1_data_fee": "Lever C: re-tune L1 data-fee scalars"}
fmt = {"eth_usd": lambda v: f"${float(v):,.0f}", "gas_growth": lambda v: f"{float(v):+.0%}",
       "l1_cost_ratio": lambda v: f"{float(v):.1%}", "spike_multiple": lambda v: f"{float(v):.2f}×",
       "induced_multiple": lambda v: f"{float(v):.0f}×", "payments_wins": lambda v: f"{float(v):.0f}",
       "fix_l1_data_fee": lambda v: "Yes" if str(v) == "True" else "No"}
rows = [[labels[k]] + [fmt.get(k, str)(a.loc[k, sc]) for sc in ["Bear", "Base", "Bull"]] for k in labels]
sc = pd.read_csv(TABLES / "model_scenarios.csv").set_index("scenario")
rows += [["→ Net revenue, no action"] + [m(sc.loc[n, "no_action_usd"]) for n in ["Bear", "Base", "Bull"]],
         ["→ Net revenue, with levers"] + [m(sc.loc[n, "total_usd"]) for n in ["Bear", "Base", "Bull"]]]
s = new_slide("3 · Business case")
x = json.loads((ROOT / "outputs" / "model.json").read_text())["inputs"]
headline(s, "Every assumption is explicit, and the observed data anchors the key ones")
table(s, pd.DataFrame(rows, columns=["Assumption", "Bear", "Base", "Bull"]), Inches(0.6), Inches(1.7), Inches(7.6),
      col_w=[3.9, 1.2, 1.2, 1.3], size=11, row_h=0.36)
panel(s, Inches(8.6), Inches(1.7), Inches(4.1), Inches(5.0))
bullets(s, [
    f"Elasticities: when blockspace got 76% cheaper, txs rose only {abs(x['observed_elasticity_txs']):.2f}% and gas "
    f"{abs(x['observed_elasticity_gas']):.2f}% per 1% price cut. A bot elasticity of −0.6 is conservative.",
    f"Congestion premium: last 12m excluding the Oct-10 crash day = {x['spike_multiple_ex_top_day']:.2f}× of the full year.",
    f"Base-load price: 90-day median {x['p_med_90d_mwei']:.2f} mwei per gas; ETH ${x['eth_usd_now']:,.0f} (30-day average).",
    f"L1 cost: DefiLlama {x['l1_ratio_llama']:.1%} of gross; growthepie {x['l1_ratio_gtp']:.1%} (Bear).",
    f"Lever B uses ether.fi's observed 90-day gas run-rate on OP Mainnet.",
], Inches(8.8), Inches(1.9), Inches(3.7), Inches(4.6), size=12)

# KPI tree
s = new_slide("3 · Measuring success")
headline(s, "How we'll know it's working: one north-star metric, four drivers, three guardrails")
k = pd.DataFrame(COPY["kpi_tree"])[["metric", "definition", "target_or_guardrail", "owner"]]
k.columns = ["Metric", "Definition", "Target / guardrail", "Owner"]
table(s, k, Inches(0.6), Inches(1.7), Inches(12.1), col_w=[2.6, 4.9, 3.3, 1.3], size=10, row_h=0.5)

# risks + next steps
s = new_slide("3 · Risks & next steps")
headline(s, "What could go wrong, and what happens in the first 90 days")
rk = pd.DataFrame(COPY["risks"])
rk.columns = ["Risk", "Mitigation"]
table(s, rk, Inches(0.6), Inches(1.7), Inches(7.0), col_w=[3.0, 4.0], size=10, row_h=0.55)
ns = COPY["next_steps_30_60_90"]
for i, d in enumerate(["30", "60", "90"]):
    y = Inches(1.6 + i * 1.78)
    panel(s, Inches(7.85), y, Inches(4.85), Inches(1.7))
    text(s, f"By day {d}", Inches(8.0), y + Inches(0.08), Inches(4.6), Inches(0.3), 12, RED, bold=True)
    bullets(s, ns[d], Inches(8.0), y + Inches(0.36), Inches(4.6), Inches(1.3), size=10, gap=1)

# ---------------------------------------------------------------- appendix
s = new_slide("Appendix")
headline(s, "Appendix A: definitions, data sources and how AI was used")
bullets(s, [
    "Our share = sequencer revenue = user fees on OP Mainnet (execution + L1 data fee, file 01) − what OP pays Ethereum to post data.",
    "L1 cost is not in the files provided. Primary source: DefiLlama op-mainnet (fees − revenue), daily; its last-12m gross differs from file 01 by "
    f"{chk.set_index('check').loc['DefiLlama gross vs file 01 gross (last 12m)', 'value']}. Cross-check: growthepie (last ~90 days). An on-chain "
    "rebuild via Blockscout was coded (external/fetch_l1_costs.py) but rate-limited.",
    "Customers: fees are assigned to the destination contract (file 06). Contracts are grouped into apps by label precedence: Allium entity → Dune "
    "namespace → display name → Dune owner. Bot = no name AND (≤5 senders/day OR ≥50 txs per sender-day).",
    "App earnings: DefiLlama fees/revenue (file 08), mapped to the same app names. Gas paid by apps is a floor (small contracts sit in 'other').",
    "Window: last 12 months = 2025-09-16 → 2026-09-15 (365 days); the prior period is compared per day because data starts 2025-01-01.",
    "AI use: Claude Code wrote the SQL/Python and ran it. Every number is produced by code, never typed in. Checks: 13 automated integrity tests "
    "(06 reconciles to 01 within 0.012%/day), cross-source L1/gross checks, and a manual read of every chart. A performance-optimizer agent "
    "had to prove its changes were output-identical, and a business-translation agent drafted copy that was checked figure-by-figure against "
    "the outputs (src/verify_copy.py).",
], Inches(0.6), Inches(1.7), Inches(12.1), Inches(5.2), size=13, gap=6)

s = new_slide("Appendix")
headline(s, "Appendix B: reproducible pipeline (one command rebuilds every number and this deck)")
steps = [["sql/01_revenue_monthly", "Gross, L1 cost, net by month"], ["sql/02_revenue_decomposition", "LMDI: volume × gas/tx × price × ETH"],
         ["sql/03_address_dim", "Address → app + segment"], ["sql/04_app_ranking", "Customer ranking, concentration, spikiness"],
         ["sql/05_segments_monthly", "Fees by segment over time"], ["sql/06_retention", "3-month logo retention + NRR"],
         ["sql/07_apps_vs_op", "App fees vs gas paid to OP"], ["sql/08_ecosystem_quarterly", "Stablecoins, bridges, CEX, TVL, users"],
         ["sql/09_fee_concentration_by_day", "Revenue concentration by day"], ["src/growth_model.py", "Scenarios, tornado, floor sweep"],
         ["src/checks.py", "13 integrity checks (build fails on any FAIL)"], ["run_all.sh", "checks → SQL → model → charts → deck"]]
table(s, pd.DataFrame(steps, columns=["Step", "What it produces"]), Inches(0.6), Inches(1.7), Inches(8.0), col_w=[3.6, 4.4],
      size=11, row_h=0.36)

s = new_slide("Appendix")
headline(s, "Appendix C: public sources")
bullets(s, [
    "DefiLlama chain fees, OP Mainnet: api.llama.fi/summary/fees/op-mainnet?dataType=dailyFees | dailyRevenue",
    "growthepie fundamentals (OP Mainnet costs_total_usd, fees_paid_usd): api.growthepie.com/v1/fundamentals.json",
    "Jovian hardfork, configurable minimum base fee: docs.optimism.io/notices/upgrade-17 ; specs.optimism.io/protocol/jovian/exec-engine.html",
    "Base leaving the Superchain (announced 2026-02-19), ether.fi moving ~70k cards to OP Mainnet, Collective buyback: dlnews.com/articles/defi/optimism-token-price-plunges-as-base-leaves-superchain/",
    "Superchain revenue share (greater of 2.5% of revenue or 15% of profit): optimism.io/blog/how-(and-why)-the-superchain-drives-fees-to-the-optimism-collective",
    "Optimism buyback (50% of Superchain revenue): cointelegraph.com/news/optimism-passes-buyback-proposal-to-bolster-op-token",
    "Base min base fee / gas configuration change (Dec 2025): reported by Base network notices; used only as a competitive reference point",
], Inches(0.6), Inches(1.7), Inches(12.1), Inches(5.2), size=13, gap=8)

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(OUT)
print(f"saved {OUT} ({page['n']} slides)")
