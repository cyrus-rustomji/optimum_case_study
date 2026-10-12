-- OP Mainnet daily activity and fees by destination address (tx to_address).
-- Window: 2025-01-01 through 2026-09-15 (inclusive).
-- Universe: every to_address that, in at least one calendar month of the window, received either
-- at least 10,000 transactions OR at least 0.25 ETH in fees (about 1,080 addresses, about 91% of fees
-- paid to a to_address). Everything else is summed into one
-- daily row with to_address = 'other' (this includes contract-creation txs, which have no to_address).
-- Fees are what the sender paid for the tx, attributed to the address the tx was sent to.
-- System deposit txs (transaction_type = 126) are excluded.
WITH
-- txs: all non-system transactions in the window
txs AS (
    SELECT
        DATE_TRUNC('day', block_timestamp)                 AS activity_date,
        DATE_TRUNC('month', block_timestamp)               AS activity_month,
        to_address,
        from_address,
        receipt_status,
        receipt_gas_used,
        receipt_gas_used * receipt_effective_gas_price     AS execution_fee_wei,
        COALESCE(receipt_l1_fee, 0)                        AS l1_data_fee_wei
    FROM optimism.raw.transactions
    WHERE block_timestamp >= '2025-01-01'
        AND block_timestamp < '2026-09-16'
        AND transaction_type <> 126
),
-- universe: addresses that clear 10,000 txs or 0.25 ETH of fees in any single month
universe AS (
    SELECT DISTINCT to_address
    FROM (
        SELECT
            to_address,
            activity_month,
            COUNT(*)                                               AS n,
            SUM(execution_fee_wei + l1_data_fee_wei) / 1e18        AS fee_eth
        FROM txs
        WHERE to_address IS NOT NULL
        GROUP BY 1, 2
    )
    WHERE n >= 10000 OR fee_eth >= 0.25
),
-- eth_price: daily median ETH/USD price
eth_price AS (
    SELECT activity_date, native_token_price_median_usd AS eth_price_usd
    FROM crosschain.metrics.overview
    WHERE chain = 'optimism'
        AND activity_date >= '2025-01-01'
        AND activity_date < '2026-09-16'
),
-- daily: roll up per day x address, collapsing non-universe addresses into 'other'
daily AS (
    SELECT
        t.activity_date,
        COALESCE(u.to_address, 'other')                    AS to_address,
        COUNT(*)                                           AS txs,
        COUNT_IF(t.receipt_status = 1)                     AS successful_txs,
        COUNT(DISTINCT t.from_address)                     AS distinct_senders,
        SUM(t.receipt_gas_used)                            AS gas_used,
        SUM(t.execution_fee_wei) / 1e18                    AS execution_fee_eth,
        SUM(t.l1_data_fee_wei) / 1e18                      AS l1_data_fee_eth
    FROM txs t
    LEFT JOIN universe u ON u.to_address = t.to_address
    GROUP BY 1, 2
)
SELECT
    TO_VARCHAR(d.activity_date, 'YYYY-MM-DD')              AS date,
    d.to_address,
    d.txs,
    d.successful_txs,
    d.distinct_senders,
    d.gas_used,
    d.execution_fee_eth,
    d.l1_data_fee_eth,
    d.execution_fee_eth + d.l1_data_fee_eth                AS total_fee_eth,
    (d.execution_fee_eth + d.l1_data_fee_eth) * p.eth_price_usd AS total_fee_usd
FROM daily d
LEFT JOIN eth_price p ON p.activity_date = d.activity_date
ORDER BY 1, d.txs DESC

-- allium_query_id: H2PVel1rKKHDhaxQPKu2
