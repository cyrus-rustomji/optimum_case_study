-- Daily median ETH/USD price, as used by Allium to value OP Mainnet fees.
-- Window: 2025-01-01 through 2026-09-15 (inclusive).
SELECT
    TO_VARCHAR(activity_date, 'YYYY-MM-DD')  AS date,
    native_token_price_median_usd            AS eth_price_usd
FROM crosschain.metrics.overview
WHERE chain = 'optimism'
    AND activity_date >= '2025-01-01'
    AND activity_date < '2026-09-16'
ORDER BY 1

-- allium_query_id: Z1cxn3kw37zK1u9ZCQft
