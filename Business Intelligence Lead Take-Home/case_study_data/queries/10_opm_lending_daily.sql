-- OP Mainnet daily lending activity by lending project, from Allium.
-- Window: 2025-01-01 through 2026-09-15 (inclusive).
-- *_volume_usd columns are daily flows (safe to sum across days).
-- tvl_usd, outstanding_loans_usd, supplied_amount_usd are end-of-day stocks (do not sum across days).
-- tvl_usd here excludes assets lent out to borrowers, so it differs from DefiLlama TVL (dataset 11).
SELECT
    TO_VARCHAR(activity_date, 'YYYY-MM-DD')  AS date,
    project,
    protocol,
    is_verified,
    deposit_volume_usd,
    withdrawal_volume_usd,
    loan_volume_usd,
    repayment_volume_usd,
    liquidation_volume_usd,
    tvl_usd,
    outstanding_loans_usd,
    supplied_amount_usd,
    active_users,
    borrower_count,
    depositor_count
FROM crosschain.metrics.lending_overview
WHERE chain = 'optimism'
    AND activity_date >= '2025-01-01'
    AND activity_date < '2026-09-16'
ORDER BY 1, supplied_amount_usd DESC NULLS LAST

-- allium_query_id: VHA5aShFk2WNhPafXdaD
