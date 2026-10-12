-- OP Mainnet daily new addresses (first-ever transaction, nonce = 0) and returning addresses.
-- Window: 2025-01-01 through 2026-09-15 (inclusive).
SELECT
    TO_VARCHAR(activity_date, 'YYYY-MM-DD')  AS date,
    new_addresses,
    returning_addresses
FROM crosschain.metrics.overview
WHERE chain = 'optimism'
    AND activity_date >= '2025-01-01'
    AND activity_date < '2026-09-16'
ORDER BY 1

-- allium_query_id: Uo2jtMSoiNs8uYoxKZIL
