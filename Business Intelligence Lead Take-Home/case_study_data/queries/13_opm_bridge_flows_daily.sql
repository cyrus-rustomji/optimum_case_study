-- OP Mainnet daily bridge flows by bridge, direction, and counterparty chain, from Allium.
-- Window: 2025-01-01 through 2026-09-15 (inclusive).
-- direction: 'inbound' = into OP Mainnet, 'outbound' = out of OP Mainnet.
-- bridge_type:
--   'canonical'          = OP Mainnet's own Standard Bridge (L2StandardBridge 0x4200...0010), Ethereum only
--   'bridge'             = application bridges (Across, Stargate, deBridge, USDT0, ...)
--   'messaging_protocol' = messaging layers (Circle CCTP, LayerZero, CCIP, Wormhole, Hyperlane, ...)
--   'bridge_aggregator'  = routers that sit on top of other bridges (Relay, LiFi, Bungee, ...)
-- Do not add bridge_aggregator volume to bridge / messaging_protocol volume: an aggregator transfer
-- can also appear as a row of the bridge it routes through.
-- events = bridge events; token_events = events that carried a priced token amount.
-- users = distinct senders (outbound) or distinct recipients (inbound).
-- usd_volume is NULL-safe; single transfers priced above $1B are treated as unpriced (bad price ticks).
-- counterparty_chain: the 25 chains with the most total USD bridge volume with OP Mainnet over the
-- window are kept by name; the other ~315 chains are grouped as 'other'.
WITH
-- app: application bridges, both directions
app AS (
    SELECT block_timestamp, 'bridge' AS bridge_type, project, direction,
           IFF(direction = 'outbound', destination_chain, source_chain) AS counterparty_chain,
           IFF(direction = 'outbound', sender_address, recipient_address) AS user_address, usd_amount
    FROM optimism.bridges.bridges_outbound_transfers
    WHERE block_timestamp >= '2025-01-01' AND block_timestamp < '2026-09-16'
    UNION ALL
    SELECT block_timestamp, 'bridge', project, direction,
           IFF(direction = 'outbound', destination_chain, source_chain),
           IFF(direction = 'outbound', sender_address, recipient_address), usd_amount
    FROM optimism.bridges.bridges_inbound_transfers
    WHERE block_timestamp >= '2025-01-01' AND block_timestamp < '2026-09-16'
),
-- msg: messaging protocols, both directions (message-only rows have NULL usd_amount)
msg AS (
    SELECT block_timestamp, 'messaging_protocol' AS bridge_type, project, direction,
           IFF(direction = 'outbound', destination_chain, source_chain) AS counterparty_chain,
           IFF(direction = 'outbound', sender_address, recipient_address) AS user_address, usd_amount
    FROM optimism.bridges.messaging_protocols_outbound_messages
    WHERE block_timestamp >= '2025-01-01' AND block_timestamp < '2026-09-16'
    UNION ALL
    SELECT block_timestamp, 'messaging_protocol', project, direction,
           IFF(direction = 'outbound', destination_chain, source_chain),
           IFF(direction = 'outbound', sender_address, recipient_address), usd_amount
    FROM optimism.bridges.messaging_protocols_inbound_messages
    WHERE block_timestamp >= '2025-01-01' AND block_timestamp < '2026-09-16'
),
-- agg: bridge aggregators, both directions
agg AS (
    SELECT block_timestamp, 'bridge_aggregator' AS bridge_type, project, direction,
           IFF(direction = 'outbound', destination_chain, source_chain) AS counterparty_chain,
           IFF(direction = 'outbound', sender_address, recipient_address) AS user_address, usd_amount
    FROM optimism.bridges.bridge_aggregators_outbound_transfers
    WHERE block_timestamp >= '2025-01-01' AND block_timestamp < '2026-09-16'
    UNION ALL
    SELECT block_timestamp, 'bridge_aggregator', project, direction,
           IFF(direction = 'outbound', destination_chain, source_chain),
           IFF(direction = 'outbound', sender_address, recipient_address), usd_amount
    FROM optimism.bridges.bridge_aggregators_inbound_transfers
    WHERE block_timestamp >= '2025-01-01' AND block_timestamp < '2026-09-16'
),
-- canonical_raw: Standard Bridge events on OP Mainnet. *Initiated = withdrawal to Ethereum (outbound),
-- *Finalized = deposit from Ethereum (inbound). The legacy duplicate events (DepositFinalized,
-- WithdrawalInitiated) are skipped so each transfer counts once.
canonical_raw AS (
    SELECT
        block_timestamp,
        name,
        IFF(name LIKE '%Initiated', 'outbound', 'inbound')                         AS direction,
        IFF(name LIKE '%Initiated', params['from']::VARCHAR, params['to']::VARCHAR) AS user_address,
        IFF(name LIKE 'ETH%', '0x0000000000000000000000000000000000000000',
            LOWER(params['localToken']::VARCHAR))                                   AS token_address,
        params['amount']::VARCHAR::NUMBER                                           AS raw_amount
    FROM optimism.decoded.logs
    WHERE block_timestamp >= '2025-01-01' AND block_timestamp < '2026-09-16'
        AND address = '0x4200000000000000000000000000000000000010'
        AND name IN ('ETHBridgeInitiated', 'ERC20BridgeInitiated', 'ETHBridgeFinalized', 'ERC20BridgeFinalized')
),
-- px: hourly USD prices on OP Mainnet (native ETH = zero address)
px AS (
    SELECT timestamp, address, price, decimals
    FROM common.prices.hourly
    WHERE timestamp >= '2025-01-01' AND timestamp < '2026-09-16'
        AND chain = 'optimism'
),
canonical AS (
    SELECT c.block_timestamp, 'canonical' AS bridge_type, 'op_standard_bridge' AS project, c.direction,
           'ethereum' AS counterparty_chain, c.user_address,
           c.raw_amount / POW(10, COALESCE(p.decimals, 18)) * p.price AS usd_amount
    FROM canonical_raw c
    LEFT JOIN px p
        ON p.timestamp = DATE_TRUNC('hour', c.block_timestamp)
        AND p.address = c.token_address
),
all_flows AS (
    SELECT * FROM app
    UNION ALL SELECT * FROM msg
    UNION ALL SELECT * FROM agg
    UNION ALL SELECT * FROM canonical
),
-- top_chains: 25 counterparty chains by total priced USD volume over the window
top_chains AS (
    SELECT counterparty_chain
    FROM all_flows
    WHERE counterparty_chain IS NOT NULL
    GROUP BY 1
    ORDER BY SUM(IFF(usd_amount <= 1e9, usd_amount, NULL)) DESC NULLS LAST
    LIMIT 25
)
SELECT
    TO_VARCHAR(DATE_TRUNC('day', f.block_timestamp), 'YYYY-MM-DD')    AS date,
    f.bridge_type,
    f.project,
    f.direction,
    CASE
        WHEN f.counterparty_chain IS NULL THEN 'unknown'
        WHEN t.counterparty_chain IS NOT NULL THEN f.counterparty_chain
        ELSE 'other'
    END                                                                AS counterparty_chain,
    COUNT(*)                                                           AS events,
    COUNT_IF(f.usd_amount IS NOT NULL AND f.usd_amount <= 1e9)             AS token_events,
    COUNT(DISTINCT f.user_address)                                     AS users,
    SUM(IFF(f.usd_amount <= 1e9, f.usd_amount, NULL))                  AS usd_volume
FROM all_flows f
LEFT JOIN top_chains t ON t.counterparty_chain = f.counterparty_chain
GROUP BY ALL
ORDER BY 1, usd_volume DESC NULLS LAST

-- allium_query_id: vbMR4NnBNELBjAGgZyTE
