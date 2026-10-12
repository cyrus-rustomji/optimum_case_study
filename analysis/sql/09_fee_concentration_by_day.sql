-- Q1: how much of the year's revenue arrives on a handful of congested days?
-- Ranks the last-12-month days by gross fee USD and reports cumulative share.
-- Also returns each day's effective price of blockspace (ETH fee per unit of L2 gas, in mwei) so spike days
-- (priority-fee auctions when blocks fill) can be told apart from busy-but-cheap days.
WITH g AS (SELECT date, sum(gas_used) AS gas_used FROM contract_activity GROUP BY 1),
d AS (
    SELECT f.date, f.total_fee_usd, f.fee_paying_txs, g.gas_used,
           f.total_fee_eth * 1e12 / g.gas_used AS mwei_per_gas
    FROM fees f JOIN g USING (date)
    WHERE f.date BETWEEN getvariable('l12m_start') AND getvariable('l12m_end')
)
SELECT date, total_fee_usd, fee_paying_txs, gas_used, mwei_per_gas,
       row_number() OVER (ORDER BY total_fee_usd DESC)                                   AS day_rank,
       sum(total_fee_usd) OVER (ORDER BY total_fee_usd DESC) / sum(total_fee_usd) OVER () AS cum_share,
       median(mwei_per_gas) OVER ()                                                      AS median_mwei_per_gas
FROM d
ORDER BY day_rank;
