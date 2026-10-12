-- OP Mainnet daily DEX volume, trade counts, and traders by DEX project, from Allium.
-- Window: 2025-01-01 through 2026-09-15 (inclusive).
-- One row per day x project x protocol (protocol = the AMM codebase/version).
-- active_users = distinct traders that day; do not sum across days.
SELECT
    TO_VARCHAR(activity_date, 'YYYY-MM-DD')  AS date,
    project,
    protocol,
    is_verified,
    total_volume_usd,
    total_swap_count,
    total_transactions,
    active_users
FROM crosschain.metrics.dex_overview
WHERE chain = 'optimism'
    AND activity_date >= '2025-01-01'
    AND activity_date < '2026-09-16'
ORDER BY 1, total_volume_usd DESC NULLS LAST

-- allium_query_id: CKNOCOYFKFhoik7Pocws
