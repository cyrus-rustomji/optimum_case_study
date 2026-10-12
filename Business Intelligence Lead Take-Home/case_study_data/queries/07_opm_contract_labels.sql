-- Labels for every address in the universe of 06_opm_contract_activity_daily.
-- Universe rule (same as 06): to_address with at least 10,000 txs OR at least 0.25 ETH of fees
-- in at least one calendar month, 2025-01-01 through 2026-09-15.
-- One row per address. Label columns are NULL where Allium has no label.
-- address_type: 'contract' if Allium has a deployment record OR the address emitted an event log in
-- the window; otherwise 'wallet'. deployed_date is NULL where Allium has no deployment record.
WITH
-- monthly: txs and fees per to_address per month
monthly AS (
    SELECT
        to_address,
        DATE_TRUNC('month', block_timestamp)                                             AS activity_month,
        COUNT(*)                                                                         AS n,
        SUM(receipt_gas_used * receipt_effective_gas_price + COALESCE(receipt_l1_fee, 0)) / 1e18 AS fee_eth
    FROM optimism.raw.transactions
    WHERE block_timestamp >= '2025-01-01'
        AND block_timestamp < '2026-09-16'
        AND transaction_type <> 126
        AND to_address IS NOT NULL
    GROUP BY 1, 2
),
-- universe: same cutoff as dataset 06
universe AS (
    SELECT DISTINCT to_address AS address
    FROM monthly
    WHERE n >= 10000 OR fee_eth >= 0.25
),
-- contracts: deployment record (absent = the address is a wallet, not a contract)
contracts AS (
    SELECT c.address, MIN(c.block_timestamp) AS deployed_at
    FROM optimism.raw.contracts c
    JOIN universe u ON u.address = c.address
    GROUP BY 1
),
-- emitters: universe addresses that emitted at least one event log in the window. Only contracts
-- emit logs, so this catches contracts missing from raw.contracts (for example, pre-2021 deployments)
emitters AS (
    SELECT DISTINCT l.address
    FROM optimism.raw.logs l
    JOIN universe u ON u.address = l.address
    WHERE l.block_timestamp >= '2025-01-01'
        AND l.block_timestamp < '2026-09-16'
),
-- entities: owner project and category from Allium's curated registry
entities AS (
    SELECT
        e.address,
        LISTAGG(DISTINCT e.project, '|')   AS entity_project,
        LISTAGG(DISTINCT e.category, '|')  AS entity_category,
        LISTAGG(DISTINCT e.name, '|')      AS entity_name
    FROM common.identity.entities e
    JOIN universe u ON u.address = e.address
    WHERE e.chain = 'optimism'
    GROUP BY 1
),
-- names: one display name per address
names AS (
    SELECT n.address, ANY_VALUE(n.name) AS display_name
    FROM common.identity.address_names n
    JOIN universe u ON u.address = n.address
    WHERE n.chain = 'optimism'
    GROUP BY 1
),
-- tags: every explorer tag on the address, pipe-separated
tags AS (
    SELECT l.address, LISTAGG(DISTINCT l.label, '|') AS tags
    FROM common.identity.address_labels l
    JOIN universe u ON u.address = l.address
    WHERE l.chain = 'optimism'
    GROUP BY 1
)
SELECT
    u.address,
    CASE
        WHEN c.address IS NOT NULL OR x.address IS NOT NULL THEN 'contract'
        ELSE 'wallet'
    END                                                 AS address_type,
    TO_VARCHAR(c.deployed_at, 'YYYY-MM-DD')             AS deployed_date,
    n.display_name,
    e.entity_project,
    e.entity_category,
    e.entity_name,
    t.tags
FROM universe u
LEFT JOIN contracts c ON c.address = u.address
LEFT JOIN emitters x  ON x.address = u.address
LEFT JOIN entities e  ON e.address = u.address
LEFT JOIN names n     ON n.address = u.address
LEFT JOIN tags t      ON t.address = u.address
ORDER BY u.address

-- allium_query_id: uFyAD9rJ6wy8WxZitQdu
