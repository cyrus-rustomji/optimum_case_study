-- OP Mainnet daily transaction fees paid by users, split into L2 execution fee and L1 data fee.
-- Window: 2025-01-01 through 2026-09-15 (inclusive).
-- Fee formula (OP Stack): execution = receipt_gas_used * receipt_effective_gas_price; L1 data = receipt_l1_fee. Both in wei.
-- System deposit txs (transaction_type = 126) pay no fee and are excluded.
-- USD values use the daily median ETH price from crosschain.metrics.overview.
WITH
-- tx_fees: one row per day, fees summed in ETH
tx_fees AS (
    SELECT
        DATE_TRUNC('day', block_timestamp)                                   AS activity_date,
        COUNT(*)                                                             AS fee_paying_txs,
        SUM(receipt_gas_used * receipt_effective_gas_price) / 1e18           AS execution_fee_eth,
        SUM(COALESCE(receipt_l1_fee, 0)) / 1e18                              AS l1_data_fee_eth
    FROM optimism.raw.transactions
    WHERE block_timestamp >= '2025-01-01'
        AND block_timestamp < '2026-09-16'
        AND transaction_type <> 126
    GROUP BY 1
),
-- eth_price: daily median ETH/USD price
eth_price AS (
    SELECT activity_date, native_token_price_median_usd AS eth_price_usd
    FROM crosschain.metrics.overview
    WHERE chain = 'optimism'
        AND activity_date >= '2025-01-01'
        AND activity_date < '2026-09-16'
)
SELECT
    TO_VARCHAR(f.activity_date, 'YYYY-MM-DD')                                AS date,
    f.fee_paying_txs,
    f.execution_fee_eth,
    f.l1_data_fee_eth,
    f.execution_fee_eth + f.l1_data_fee_eth                                  AS total_fee_eth,
    p.eth_price_usd,
    f.execution_fee_eth * p.eth_price_usd                                    AS execution_fee_usd,
    f.l1_data_fee_eth * p.eth_price_usd                                      AS l1_data_fee_usd,
    (f.execution_fee_eth + f.l1_data_fee_eth) * p.eth_price_usd              AS total_fee_usd
FROM tx_fees f
LEFT JOIN eth_price p ON p.activity_date = f.activity_date
ORDER BY 1

-- allium_query_id: igRA7xwFxb86UkjE2y32
