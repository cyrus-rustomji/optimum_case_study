#!/usr/bin/env python3
"""
Fetch what OP Mainnet pays Ethereum (L1) to operate, from two independent public sources.

Source A - DefiLlama chain fees for `op-mainnet`:
    dailyFees    = gas fees paid by users on OP Mainnet
    dailyRevenue = fees minus L1 posting costs (DefiLlama L2 methodology)
    -> implied L1 cost = dailyFees - dailyRevenue

Source C - growthepie fundamentals.json (fees_paid_usd, costs_total_usd); public file only keeps ~90 days.

Source B - on-chain reconstruction from Ethereum via Blockscout (no API key):
    Batcher  0x6887246668a3b87F54DeB3b94Ba47a6f63F32985 -> Batch Inbox 0xFF00...0010
    Proposer 0x473300df21D047806A082244b417f96b32f13A33 (output roots / dispute games)
    execution cost = gasUsed * gasPrice for every tx (exact, from txlist)
    blob cost      = burnt_blob_fee, sampled N txs per day and scaled by that day's tx count

Outputs (external/):
    raw/llama_op-mainnet_{dailyFees,dailyRevenue}.json
    raw/blockscout_{batcher,proposer}_txlist.csv
    raw/blockscout_blob_sample.csv
    l1_costs_daily.csv   (date, llama_fees_usd, llama_revenue_usd, llama_l1_cost_usd,
                          onchain_txs, onchain_exec_cost_eth, onchain_blob_cost_eth, onchain_l1_cost_eth)
Run:  .venv/bin/python external/fetch_l1_costs.py   (resumable; cached raw files are reused)
"""
import csv
import datetime as dt
import json
import random
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
RAW.mkdir(exist_ok=True)
START, END = dt.date(2025, 1, 1), dt.date(2026, 9, 15)
BATCHER = "0x6887246668a3b87F54DeB3b94Ba47a6f63F32985"
PROPOSER = "0x473300df21D047806A082244b417f96b32f13A33"
BS = "https://eth.blockscout.com/api"
SAMPLES_PER_DAY = 2  # per sampled day
SAMPLE_EVERY_N_DAYS = 7  # blob fees are sampled weekly and the weekly mean is applied to every day of that week
random.seed(42)


def get(url, tries=40):
    """GET JSON with throttling; Blockscout's free tier returns 429 (or status 0) when we go too fast."""
    for i in range(tries):
        time.sleep(0.4)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "op-bi-case-study/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            if isinstance(d, dict) and d.get("status") == "0" and "Too many" in str(d.get("message")):
                raise RuntimeError("rate limited")
            return d
        except Exception as e:  # noqa: BLE001 - network retries
            wait = min(15 * (i + 1), 180)
            print(f"  retry {i+1} in {wait}s: {e}", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"failed: {url}")


def llama():
    out = {}
    for t in ["dailyFees", "dailyRevenue"]:
        p = RAW / f"llama_op-mainnet_{t}.json"
        if not p.exists():
            p.write_text(json.dumps(get(f"https://api.llama.fi/summary/fees/op-mainnet?dataType={t}")))
        d = json.loads(p.read_text())
        out[t] = {dt.datetime.utcfromtimestamp(ts).date(): v for ts, v in d["totalDataChart"]}
    return out


def growthepie():
    """Source C: growthepie public fundamentals (rolling last ~90 days only). Used as a cross-check."""
    p = RAW / "gtp_fundamentals.json"
    if not p.exists():
        p.write_text(json.dumps(get("https://api.growthepie.com/v1/fundamentals.json")))
    out = defaultdict(dict)
    for r in json.loads(p.read_text()):
        if r["origin_key"] == "optimism" and r["metric_key"] in ("fees_paid_usd", "costs_total_usd"):
            out[dt.date.fromisoformat(r["date"])][r["metric_key"]] = r["value"]
    return out


def block_at(day):
    f = RAW / f"block_at_{day}.txt"
    if f.exists():
        return int(f.read_text())
    ts = int(dt.datetime.combine(day, dt.time()).replace(tzinfo=dt.timezone.utc).timestamp())
    r = get(f"{BS}?module=block&action=getblocknobytime&timestamp={ts}&closest=after")
    f.write_text(r["result"]["blockNumber"])
    return int(r["result"]["blockNumber"])


def txlist(addr, name, b0, b1):
    """All txs sent by `addr` between L1 blocks b0..b1. Each ~7-day chunk is cached so a rate-limited run can resume."""
    cache = RAW / f"blockscout_{name}_chunks"
    cache.mkdir(exist_ok=True)
    rows, start, step = [], b0, 50_000  # ~7 days of L1 blocks; the batcher sends ~1.3k tx per window
    while start <= b1:
        end = min(start + step - 1, b1)
        f = cache / f"{start}_{end}.json"
        if f.exists():
            res = json.loads(f.read_text())
        else:
            r = get(f"{BS}?module=account&action=txlist&address={addr}&startblock={start}&endblock={end}"
                    f"&page=1&offset=10000&sort=asc")
            res = r.get("result") or []
            if len(res) >= 10000:
                raise RuntimeError("chunk hit the 10k page cap; reduce step")
            res = [{k: x[k] for k in ["hash", "blockNumber", "timeStamp", "from", "to", "gasUsed", "gasPrice",
                                      "isError"]} for x in res if x["from"].lower() == addr.lower()]
            f.write_text(json.dumps(res))
            print(f"  {name} blocks {start}-{end}: {len(res)}", flush=True)
        rows += res
        start = end + 1
    return rows


def blob_sample(batcher_rows):
    p = RAW / "blockscout_blob_sample.csv"
    done = {r["hash"]: r for r in csv.DictReader(p.open())} if p.exists() else {}
    by_day = defaultdict(list)
    for r in batcher_rows:
        by_day[dt.datetime.utcfromtimestamp(int(r["timeStamp"])).date()].append(r["hash"])
    want = []
    for day, hs in sorted(by_day.items()):
        if (day - START).days % SAMPLE_EVERY_N_DAYS:
            continue
        have = [h for h in hs if h in done]
        need = max(0, SAMPLES_PER_DAY - len(have))
        want += [(day, h) for h in random.sample([h for h in hs if h not in done], min(need, len(hs) - len(have)))]
    print(f"  blob sample: {len(done)} cached, {len(want)} to fetch")
    new = p.exists()
    with p.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "hash", "blob_gas_used", "blob_gas_price", "burnt_blob_fee"])
        if not new:
            w.writeheader()
        for i, (day, h) in enumerate(want):
            t = get(f"{BS}/v2/transactions/{h}")
            w.writerow({"date": day.isoformat(), "hash": h, "blob_gas_used": t.get("blob_gas_used") or 0,
                        "blob_gas_price": t.get("blob_gas_price") or 0,
                        "burnt_blob_fee": t.get("burnt_blob_fee") or 0})
            if i % 100 == 0:
                f.flush()
                print(f"    {i}/{len(want)}")
    return list(csv.DictReader(p.open()))


def main():
    ll = llama()
    gtp = growthepie()
    try:
        if "--skip-onchain" in sys.argv:
            raise RuntimeError("skipped by flag")
        b0, b1 = block_at(START), block_at(END + dt.timedelta(days=1)) - 1
        print(f"L1 blocks {b0}..{b1}")
        bat = txlist(BATCHER, "batcher", b0, b1)
        pro = txlist(PROPOSER, "proposer", b0, b1)
        sample = blob_sample(bat)
    except RuntimeError as e:
        # Blockscout's keyless tier rate-limits hard (HTTP 429). The on-chain columns are then left empty and the
        # analysis falls back to DefiLlama (primary) and growthepie (cross-check); see README "L1 cost sources".
        print(f"on-chain reconstruction unavailable: {e}")
        bat, pro, sample = [], [], []

    day = lambda r: dt.datetime.utcfromtimestamp(int(r["timeStamp"])).date()  # noqa: E731
    exec_eth, ntx = defaultdict(float), defaultdict(int)
    for r in bat + pro:
        d = day(r)
        exec_eth[d] += int(r["gasUsed"]) * int(r["gasPrice"]) / 1e18
    for r in bat:
        ntx[day(r)] += 1
    blob_mean = defaultdict(list)  # keyed by the first day of each 7-day sampling week
    for s in sample:
        blob_mean[dt.date.fromisoformat(s["date"])].append(int(s["burnt_blob_fee"]) / 1e18)
    week_start = lambda d: d - dt.timedelta(days=(d - START).days % SAMPLE_EVERY_N_DAYS)  # noqa: E731

    with (HERE / "l1_costs_daily.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "llama_fees_usd", "llama_revenue_usd", "llama_l1_cost_usd", "onchain_batcher_txs",
                    "onchain_blob_samples", "onchain_exec_cost_eth", "onchain_blob_cost_eth", "onchain_l1_cost_eth",
                    "gtp_fees_usd", "gtp_l1_cost_usd"])
        d = START
        while d <= END:
            fees, rev = ll["dailyFees"].get(d), ll["dailyRevenue"].get(d)
            bm = blob_mean.get(week_start(d), [])
            blob = (sum(bm) / len(bm)) * ntx[d] if bm else 0.0
            oc = bool(bat)
            w.writerow([d, fees, rev, None if fees is None or rev is None else fees - rev,
                        ntx[d] if oc else None, len(bm) if oc else None,
                        exec_eth[d] if oc else None, blob if oc else None, exec_eth[d] + blob if oc else None,
                        gtp.get(d, {}).get("fees_paid_usd"), gtp.get(d, {}).get("costs_total_usd")])
            d += dt.timedelta(days=1)
    print("wrote l1_costs_daily.csv")


if __name__ == "__main__":
    main()
