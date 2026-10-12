-- Q1/Q2: monthly gross fees and txs by customer segment (whole data window, for the trend chart).
-- Requires address_dim (03).
SELECT date_trunc('month', c.date)::DATE AS month,
       d.segment,
       sum(c.txs)            AS txs,
       sum(c.total_fee_usd)  AS fee_usd,
       sum(c.total_fee_eth)  AS fee_eth,
       sum(c.gas_used)       AS gas_used
FROM contract_activity c
JOIN address_dim d ON d.address = c.to_address
GROUP BY ALL
ORDER BY 1, 2;
