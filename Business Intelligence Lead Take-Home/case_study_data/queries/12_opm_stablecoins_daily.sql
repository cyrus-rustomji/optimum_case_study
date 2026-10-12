-- OP Mainnet daily stablecoin supply and transfer activity per stablecoin token, from Allium.
-- Window: 2025-01-01 through 2026-09-15 (inclusive).
-- One row per day x token contract. Each OP Mainnet token contract is counted once, so summing
-- supply across tokens on one day gives OP Mainnet total stablecoin supply.
-- circulating_supply_usd = total supply minus issuer treasury / pre-minted balances.
-- is_native = TRUE for issuer-deployed tokens (e.g. native USDC), FALSE for bridged copies (e.g. USDC.e).
-- transfer_volume_usd counts every transfer, including contract and bot transfers that loop the same
-- dollars many times a day. adjusted_volume_usd is Allium's filtered version: it removes transfers
-- Allium classifies as inorganic (bots, internal contract hops) and keeps payments, trading, and savings.
WITH
-- supply: end-of-day supply per token
supply AS (
    SELECT
        date,
        token_address,
        token_symbol,
        product_id,
        currency,
        is_native,
        total_supply_usd,
        circulating_supply_usd
    FROM stablecoins.core.supply_daily
    WHERE chain = 'optimism'
        AND date >= '2025-01-01'
        AND date < '2026-09-16'
),
-- volume: daily transfer activity per token
volume AS (
    SELECT
        activity_date,
        token_address,
        token_symbol,
        product_id,
        currency,
        is_native,
        transfer_tx_count,
        transfer_count,
        transfer_volume_usd,
        adjusted_volume_usd,
        sender_count,
        recipient_count
    FROM stablecoins.metrics.volume_daily
    WHERE chain = 'optimism'
        AND activity_date >= '2025-01-01'
        AND activity_date < '2026-09-16'
)
SELECT
    TO_VARCHAR(COALESCE(s.date, v.activity_date), 'YYYY-MM-DD')  AS date,
    COALESCE(s.token_address, v.token_address)                  AS token_address,
    COALESCE(s.token_symbol, v.token_symbol)                    AS token_symbol,
    COALESCE(s.product_id, v.product_id)                        AS product_id,
    COALESCE(s.currency, v.currency)                            AS currency,
    COALESCE(s.is_native, v.is_native)                          AS is_native,
    s.total_supply_usd,
    s.circulating_supply_usd,
    v.transfer_tx_count,
    v.transfer_count,
    v.transfer_volume_usd,
    v.adjusted_volume_usd,
    v.sender_count,
    v.recipient_count
FROM supply s
FULL OUTER JOIN volume v
    ON v.activity_date = s.date
    AND v.token_address = s.token_address
ORDER BY 1, s.circulating_supply_usd DESC NULLS LAST

-- allium_query_id: DCER7hESwhtupAQfxtuN
