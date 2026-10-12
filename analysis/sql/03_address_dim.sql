-- Q2: one row per destination address in file 06 with an app name and a customer segment.
--
-- App name precedence (most to least trustworthy for "who owns this contract"):
--   1. Allium entity_project               (curated entity registry)
--   2. Dune decoded namespace, first token that is not a generic wallet framework (gnosis_safe)
--   3. Allium display_name                 (e.g. "Trading Bot", "StrategyExecutor")
--   4. Dune owner, except 'sushiswap' and 'Gnosis Safe' which Dune attaches to many unrelated
--      contracts in this file (checked by eye: Multicall3, LayerZero Executor, Squid all "owned" by sushiswap)
--   5. Dune CEX name
-- Names are normalised (lower case, version suffixes and _finance/_protocol/xyz stripped, aliases merged)
-- so that e.g. velodrome_v2 / velodrome_finance / velodrome land on one app.
--
-- Segment rules:
--   long_tail        : the 'other' bucket (addresses under 10k tx and 0.25 ETH in every month, + contract creations)
--   mev_bots         : labelled mev / trading / market_maker, or named "Trading Bot" / "StrategyExecutor"
--   named_app        : any other address with an app name
--   unlabeled_bot    : no name, and automated: <= 5 distinct senders on an average active day, OR >= 50 txs per
--                      sender-day (a person does not send 50+ txs a day to one contract; median named app = 4.5)
--   unlabeled_multi  : no name, many senders each sending a few txs (looks like real users of an unnamed app)
CREATE OR REPLACE TABLE address_dim AS
WITH stats AS (
    SELECT to_address AS address,
           avg(distinct_senders)                               AS avg_daily_senders,
           sum(txs)                                            AS txs_all,
           sum(txs) / nullif(sum(distinct_senders), 0)         AS txs_per_sender_day,
           sum(total_fee_eth) / nullif(sum(txs), 0)            AS eth_per_tx_all
    FROM contract_activity
    GROUP BY 1
),
raw AS (
    SELECT
        l.address, l.address_type, l.entity_category, l.display_name, l.dune_cex_name,
        lower(coalesce(
            l.entity_project,
            nullif(trim(list_filter(string_split(l.dune_namespace, '|'),
                                    x -> trim(x) NOT IN ('gnosis_safe', 'erc4337', 'superchain'))[1]), ''),
            CASE WHEN l.display_name IN ('Trading Bot', 'StrategyExecutor', 'Order Manager', 'Router') THEN NULL
                 ELSE l.display_name END,
            CASE WHEN l.dune_owner NOT IN ('sushiswap', 'Gnosis Safe') THEN l.dune_owner END,
            l.dune_cex_name,
            nullif(trim(string_split(l.dune_namespace, '|')[1]), '')
        )) AS raw_name
    FROM labels l
),
norm AS (
    SELECT *,
        regexp_replace(
            regexp_replace(
                regexp_replace(split_part(raw_name, ':', 1), '_v[0-9].*$|_beta$', ''),
            '(_finance|_protocol|_network|_platform|xyz|_xyz|_faircrypto)$', ''),
        '\s+', ' ', 'g') AS n1
    FROM raw
)
SELECT
    coalesce(n.address, s.address)                            AS address,
    n.address_type,
    CASE
        WHEN s.address = 'other' THEN 'long tail (other)'
        WHEN n.n1 IS NULL THEN NULL
        ELSE CASE n.n1
            WHEN 'etherfi' THEN 'ether.fi'
            WHEN 'layer_zero' THEN 'layerzero'
            WHEN 'farcasterxyz' THEN 'farcaster'
            WHEN 'oneinch' THEN '1inch'
            WHEN 'zeroex' THEN '0x'
            WHEN '0x api' THEN '0x'
            WHEN 'optimism_usdc' THEN 'circle'
            WHEN 'circle internet financial, llc.' THEN 'circle'
            WHEN 'usdt' THEN 'tether'
            WHEN 'odos_v3_router' THEN 'odos'
            WHEN 'kyber' THEN 'kyberswap'
            WHEN 'okx_dex' THEN 'okx'
            WHEN 'hyperlane' THEN 'hyperlane'
            WHEN 'reservoir' THEN 'relay'
            WHEN 'eth_infinitism_account_abstraction' THEN 'erc4337 entrypoint'
            WHEN 'alchemy' THEN 'erc4337 entrypoint'
            WHEN 'alchemyplatform' THEN 'erc4337 entrypoint'
            WHEN 'attestationstation' THEN 'ethereum_attestation_service'
            WHEN 'stargate' THEN 'stargate'
            WHEN 'rango_exchange' THEN 'rango'
            WHEN 'xen_crypto' THEN 'xen crypto'
            WHEN 'null address' THEN 'null address'
            WHEN 'hyperlane_token' THEN 'hyperlane'
            WHEN 'gasdotzip' THEN 'gas.zip'
            WHEN 'mayan_swift' THEN 'mayan'
            WHEN 'holonym_foundation' THEN 'holonym'
            WHEN 'synthetix_futuresmarket' THEN 'synthetix'
            WHEN 'perpetual' THEN 'perp'
            WHEN 'walletconnect_optimism' THEN 'walletconnect'
            WHEN 'optimism_governor' THEN 'op'
            ELSE n.n1 END
    END                                                         AS app,
    CASE
        WHEN s.address = 'other' THEN 'long_tail'
        WHEN n.entity_category IN ('mev', 'trading', 'market_maker')
          OR n.display_name IN ('Trading Bot', 'StrategyExecutor') THEN 'mev_bots'
        WHEN n.n1 IS NOT NULL THEN 'named_app'
        WHEN s.avg_daily_senders <= 5 OR s.txs_per_sender_day >= 50 THEN 'unlabeled_bot'
        ELSE 'unlabeled_multi'
    END                                                         AS segment,
    n.entity_category,
    s.avg_daily_senders,
    s.txs_per_sender_day,
    s.txs_all,
    s.eth_per_tx_all
FROM stats s
LEFT JOIN norm n ON n.address = s.address;

SELECT segment, count(*) AS addresses, count(app) AS named FROM address_dim GROUP BY 1 ORDER BY 2 DESC;
