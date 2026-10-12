-- OP Mainnet daily transaction counts and active senders.
-- Window: 2025-01-01 through 2026-09-15 (inclusive).
-- total_transactions includes failed txs and the one system deposit tx per block.
-- active_addresses = distinct addresses that sent at least one successful tx that day.
SELECT
    TO_VARCHAR(activity_date, 'YYYY-MM-DD')  AS date,
    total_transactions,
    success_transactions,
    failed_transactions,
    active_addresses,
    active_contracts
FROM crosschain.metrics.overview
WHERE chain = 'optimism'
    AND activity_date >= '2025-01-01'
    AND activity_date < '2026-09-16'
ORDER BY 1

-- allium_query_id: g5CDw0CHix6YFosHlKA7
