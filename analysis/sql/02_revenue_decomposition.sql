-- Q1: why did gross sequencer revenue change? Additive LMDI decomposition of USD revenue per day.
-- revenue/day = txs/day * gas/tx * ETH fee per unit gas * USD per ETH
--   txs/day        -> demand volume
--   gas/tx         -> what each tx does (complexity / tx mix)
--   ETH per gas    -> price of blockspace (base fee + priority fee + L1 data fee per gas)
--   USD per ETH    -> ETH price effect (fee-weighted)
-- LMDI: effect_k = L(R1, R0) * ln(x1_k / x0_k), L(a,b) = (a-b)/(ln a - ln b). The effects sum exactly to R1 - R0.
-- Periods compared on a per-day basis so unequal lengths don't bias the result.
WITH periods(period, p_start, p_end, ord) AS (
    VALUES ('Prior: Jan 1 - Sep 15 2025', DATE '2025-01-01', DATE '2025-09-15', 0),
           ('Last 12m: Sep 16 2025 - Sep 15 2026', DATE '2025-09-16', DATE '2026-09-15', 1),
           ('Summer 2025 (Jun-Aug)', DATE '2025-06-01', DATE '2025-08-31', 2),
           ('Summer 2026 (Jun-Aug)', DATE '2026-06-01', DATE '2026-08-31', 3)
),
gas AS (
    SELECT date, sum(gas_used) AS gas_used FROM contract_activity GROUP BY 1
),
p AS (
    SELECT
        period, ord,
        count(*)                                              AS days,
        sum(f.fee_paying_txs) / count(*)                      AS txs_per_day,
        sum(g.gas_used) / sum(f.fee_paying_txs)               AS gas_per_tx,
        sum(f.total_fee_eth) / sum(g.gas_used)                AS eth_per_gas,
        sum(f.total_fee_eth * f.eth_price_usd) / sum(f.total_fee_eth) AS usd_per_eth,
        sum(f.total_fee_eth * f.eth_price_usd) / count(*)     AS usd_per_day
    FROM periods
    JOIN fees f ON f.date BETWEEN p_start AND p_end
    JOIN gas g USING (date)
    GROUP BY ALL
),
pairs AS (
    SELECT a.period AS base_period, b.period AS comp_period,
           a.usd_per_day AS r0, b.usd_per_day AS r1,
           (b.usd_per_day - a.usd_per_day) / (ln(b.usd_per_day) - ln(a.usd_per_day)) AS lw,
           a.txs_per_day AS t0, b.txs_per_day AS t1, a.gas_per_tx AS g0, b.gas_per_tx AS g1,
           a.eth_per_gas AS e0, b.eth_per_gas AS e1, a.usd_per_eth AS u0, b.usd_per_eth AS u1
    FROM p a JOIN p b ON (a.ord, b.ord) IN ((0, 1), (2, 3))
)
SELECT base_period, comp_period, r0 AS usd_per_day_base, r1 AS usd_per_day_comp, r1 - r0 AS change_usd_per_day,
       lw * ln(t1 / t0) AS effect_tx_volume,
       lw * ln(g1 / g0) AS effect_gas_per_tx,
       lw * ln(e1 / e0) AS effect_blockspace_price,
       lw * ln(u1 / u0) AS effect_eth_price,
       t1 / t0 - 1 AS pct_tx_volume, g1 / g0 - 1 AS pct_gas_per_tx, e1 / e0 - 1 AS pct_blockspace_price, u1 / u0 - 1 AS pct_eth_price
FROM pairs
ORDER BY base_period DESC;
