-- OP Mainnet daily centralized-exchange (CEX) deposits and withdrawals by exchange and token, from Allium.
-- Window: 2025-01-01 through 2026-09-15 (inclusive).
-- amount_in / usd_amount_in = tokens deposited TO the exchange's OP Mainnet addresses (including user
-- deposit addresses). amount_out / usd_amount_out = tokens withdrawn FROM the exchange to OP Mainnet.
-- net_usd_amount = usd_amount_in - usd_amount_out (positive = net flow into the exchange).
-- Allium publishes this table pre-aggregated: it has USD and token volumes, not transfer counts.
-- Coverage is limited to addresses Allium attributes to an exchange, so totals are a lower bound.
SELECT
    TO_VARCHAR(date, 'YYYY-MM-DD')  AS date,
    entity                          AS exchange,
    token_address,
    token_symbol,
    amount_in,
    amount_out,
    usd_amount_in,
    usd_amount_out,
    net_usd_amount
FROM allium_identity.aggregates.cex_deposits_withdrawals
WHERE chain = 'optimism'
    AND date >= '2025-01-01'
    AND date < '2026-09-16'
ORDER BY 1, usd_amount_in DESC NULLS LAST

-- allium_query_id: YhT3lRv572InnQoEM2Pf
