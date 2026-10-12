-- OP Mainnet daily contract deployments and distinct deployer addresses.
-- Window: 2025-01-01 through 2026-09-15 (inclusive).
-- new_deployed_contracts counts every created contract, including contracts created by factories.
SELECT
    TO_VARCHAR(activity_date, 'YYYY-MM-DD')  AS date,
    new_deployed_contracts,
    distinct_contract_deployers
FROM crosschain.metrics.overview
WHERE chain = 'optimism'
    AND activity_date >= '2025-01-01'
    AND activity_date < '2026-09-16'
ORDER BY 1

-- allium_query_id: F41T0GBRqEards0lHYeQ
