# Findings brief: OP Mainnet revenue (input for the deck copy)

Every number here comes from `outputs/headline.json`, `outputs/model.json` or `outputs/tables/*.csv`.
The window is the **last 12 months (L12M) = 2025-09-16 → 2026-09-15**. "Prior" = 2025-01-01 → 2025-09-15, which is all
the data before the window (258 days), so comparisons are made **per day**.

## Leadership's question
"Who is making money on OP Mainnet, how much is our share, and how can we grow our take over the next 12 months?"
"Our share" = sequencer revenue = the fees users pay on OP Mainnet minus what OP pays to post data to Ethereum.

## 1. Our share (diagnosis)
- L12M gross user fees: **$1.256M** (430 ETH). Execution fee = 98.4% of it, L1 data fee = $20k.
- L1 cost: **$40k** (DefiLlama op-mainnet fees − revenue), so **net sequencer revenue = $1.216M, a 96.8% margin**.
  Cross-check: growthepie puts the L1 cost at 5.6% of gross over the 64 days where the two sources overlap, vs 2.1% for DefiLlama
  over the same days. Either way net ≈ 95–97% of gross. An on-chain rebuild from the batcher's Ethereum txs was attempted,
  but the free Blockscout API rate-limited it.
- Run-rate: gross fees per day fell **70%**, from $11.6k (prior) to $3.4k (L12M). The last 3 full months (Jun–Aug 2026)
  average **$50.5k/month gross ($49.7k net)**, against $680k in Jan 2025.
- Why (additive LMDI decomposition of $/day, prior → L12M, change −$8.2k/day):
  - txs/day **+71%** (1.03M → 1.76M) → +$3.6k/day
  - gas per tx **−35%** → −$2.9k/day
  - **price of blockspace (ETH fee per unit gas) −76%** → **−$9.5k/day** ← the main driver
  - ETH price +8% (fee-weighted) → +$0.5k/day
  - So: OP sells more blockspace than ever, but at a fraction of the price. Daily active addresses fell from ~81k (Jan 2025)
    to ~21k (Aug 2026), while txs doubled → the volume is automated.
- Natural experiment: blockspace got 76% cheaper, and txs rose only 0.38% per 1% price drop while gas rose 0.08%.
  **Demand is price-inelastic.** Cutting the price did not buy volume.
- Revenue is **event-driven**: the median day's blockspace price is 1.28 mwei/gas. **Oct 10 2025 (market crash) alone earned $250k,
  20% of the year**, at 73× the median price. The 10 busiest days = **32%** of L12M fees.
  ~40% of L12M fees (173 of 430 ETH) is a "congestion premium" above the median price.
- L1 data leg: since Oct 2025 users pay *less* L1 data fee than OP's L1 cost (about −$20k/yr). The fee scalars are stale.

## 2. Who makes money / customers
- **Apps earned $41.3M in fees in the L12M (DefiLlama) and kept $17.4M as revenue. OP's gross take was $1.26M** (about 3% of what
  apps collect). The gas paid by the tracked contracts of those apps = **$111k**.
  - ether.fi (card issuer; moved ~70k cards to OP Mainnet in 2026): **$18.5M app fees, $7.1M revenue; its contracts paid OP $10k**
    in gas = 1,849× app fees per $1 of gas.
  - Uniswap $3.75M / $27k gas; Velodrome $3.36M (all kept as revenue) / $7.6k gas; Chainlink $3.0M / $21k; Aave $2.1M / $0.6k.
- Customers = whoever's transactions pay the sequencer (fees attributed to the destination contract, file 06):
  - **Unnamed automated contracts (bots): 57% of fees, 86% of txs**
  - Labelled MEV/trading bots: 9% of fees, 1% of txs
  - Long tail (small contracts): 11% of fees
  - Unnamed multi-user contracts: 5%
  - **Named apps & infra: 18% of fees, 8% of txs**
  - → about two-thirds of OP's revenue is paid by bots. Named apps pay little.
- Concentration: 724 customers. **Top 10 = 50% of fees, top 50 = 81%**, HHI 443. 7 of the top 10 are bots/MEV.
  Some searchers pay up to $350 per tx on spike days (priority-fee auctions).
- Churn: of addresses paying ≥$10/month, only **~53%** still pay 3 months later. Their 3-month net revenue retention averages **43%**.
- Other customer targets (quarterly, Q3 2025 → Q3 2026 to Sep 15, flows normalised to 91 days):
  - Stablecoin issuers/payments: **adjusted stablecoin transfer volume +67%** ($1.08B → $1.81B/qtr), but native stable
    supply fell to $208M from $279M, and bridged to $268M from $382M.
  - Bridges: inflows now exceed outflows ($1.08B in vs $0.71B out per quarter). In Q3 2025 it was the reverse ($1.40B in vs $1.65B out).
  - CEXs: deposits+withdrawals $4.5B/qtr (down from $9.4B). Binance is the largest channel.
  - DeFi TVL $344M (from $438M); DEX volume $1.5B/qtr (from $4.6B).
  - Users: new addresses 0.48M/qtr (from 2.06M).
  - Builders: average daily deployers ~1.8k (flat to slightly up).
  - Superchain context (public): Base announced on 2026-02-19 that it is leaving the Superchain revenue share (it had been ~90% of
    Collective inflows), and governance approved spending 50% of Collective revenue on OP buybacks. This makes OP Mainnet's own
    sequencer margin, and **chains as paying "OP Enterprise" customers**, matter more.

## 3. Business case (next 12 months, net sequencer revenue)
Model: net = (base-load gas × price + congestion premium) × ETH/USD × (1 − L1 cost ratio). Levers are additive lines.
- **No action (Base): $0.90M** (−26% vs L12M $1.22M): ETH at $2,388, no Oct-10-sized crash (congestion premium 0.67× last year,
  which is last year excluding the top day), flat gas.
- **Lever A: minimum base fee** (Jovian `minBaseFee`, live on the OP Stack since Dec 2025): floor at 2.5 mwei/gas,
  about 1.8× today's 90-day median of 1.36. Assumes bot elasticity −0.6 (conservative: observed −0.38 for txs, −0.08 for gas) and
  user elasticity −0.1. → **+$215k**. Bot gas −31%, user gas −6%. A typical user tx (234k gas) costs **$0.0014**.
- **Lever B: payments BD**: 2 more issuers of ether.fi's scale, ×2 induced activity → **+$51k**. Small for the sequencer.
  Its value is in ecosystem fees, stablecoin volume and TVL.
- **Lever C: re-tune the L1 data fee scalars** so the data leg breaks even → **+$20k**.
- **Base with levers: $1.19M** (+32% vs no action, about flat vs L12M). **Bear $0.40M. Bull $3.09M.**
- Tornado (one at a time around $1.19M): ETH price ±40% → $0.72M–$1.66M; min base fee 1.5–4.0 mwei → $0.98M–$1.44M;
  bot elasticity −1.2/−0.3 → $0.98M–$1.33M; organic gas ±20% → $1.02M–$1.36M; congestion 0.25×–1.0× → $1.02M–$1.32M;
  payments wins 0–4 → $1.14M–$1.24M; L1 cost source → $1.16M–$1.19M.
- Floor sweep (Base elasticities, without B/C): 1.5 mwei $0.93M, 2.0 $1.03M, 2.5 $1.12M, 3.0 $1.20M, 4.0 $1.34M, 5.0 $1.47M.

## Caveats
- File 06 assigns fees to the destination address (it can be a router or bot). Labels cover ~340 of the 1,082 addresses, and
  "bot" is a heuristic (≤5 senders/day or ≥50 txs per sender-day).
- App fees come from DefiLlama (USD at its prices), and some apps' contracts sit below file 06's threshold → gas paid by apps is a floor.
- The elasticity of bot demand to a price *floor* is the biggest unknown. The recommendation is to test it with a staged rollout.
- Competitive risk: Base's min base fee is 0.5 mwei. If OP is too high, flow may migrate to Base, Arbitrum or other chains.
- OP Mainnet's current `minBaseFee` setting was not verified in this analysis. Check the SystemConfig/superchain-registry before acting.
