-- Q1/Q2: who is making money? What apps earn (DefiLlama, file 08) next to what their users pay OP (file 06).
-- Last 12 months. DefiLlama protocol slugs are mapped to the app names from 03_address_dim where they differ.
-- "pays OP" only covers addresses that clear file 06's per-address threshold; small contracts sit in 'other',
-- so it is a floor, not an exact figure.
WITH alias(protocol, app) AS (
    VALUES ('compound-finance', 'compound'), ('li.fi', 'lifi'), ('lets-get-hai', 'hai'), ('sushi', 'sushiswap'),
           ('curve-finance', 'curve'), ('woofi', 'woonetwork'), ('extra-finance', 'extra'),
           ('stargate-finance', 'stargate'), ('mayan-finance', 'mayan'), ('uniswap-labs', 'uniswap'),
           ('socket-protocol', 'bungee'), ('human-protocol', 'holonym')
),
earn AS (
    SELECT coalesce(a.app, f.protocol) AS app,
           string_agg(DISTINCT f.protocol, ', ' ORDER BY f.protocol) AS defillama_protocols,
           arg_max(f.category, f.fee_usd) AS category,  -- category of the app's largest fee day (some apps carry two)
           sum(f.fee_usd) AS app_fees_usd,
           sum(f.revenue_usd) AS app_revenue_usd,
           sum(f.holder_revenue_usd) AS app_holder_revenue_usd
    FROM app_fees f LEFT JOIN alias a USING (protocol)
    WHERE f.date BETWEEN getvariable('l12m_start') AND getvariable('l12m_end')
    GROUP BY 1
),
pay AS (
    SELECT d.app, sum(c.total_fee_usd) AS paid_op_usd, sum(c.txs) AS txs
    FROM contract_activity c JOIN address_dim d ON d.address = c.to_address
    WHERE c.date BETWEEN getvariable('l12m_start') AND getvariable('l12m_end') AND d.app IS NOT NULL
    GROUP BY 1
)
SELECT e.app, e.defillama_protocols, e.category, e.app_fees_usd, e.app_revenue_usd, e.app_holder_revenue_usd,
       coalesce(p.paid_op_usd, 0) AS paid_op_usd,
       p.txs,
       e.app_fees_usd / nullif(p.paid_op_usd, 0) AS app_fees_per_1usd_gas,
       p.paid_op_usd IS NOT NULL AS has_tracked_contracts
FROM earn e LEFT JOIN pay p USING (app)
WHERE e.app_fees_usd > 0
ORDER BY e.app_fees_usd DESC;
