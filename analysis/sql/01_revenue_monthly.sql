-- Q1: OP Mainnet sequencer revenue by month.
-- gross   = what users paid on OP Mainnet: execution fee + L1 data fee (file 01, file 02 prices)
-- l1_cost = what OP paid Ethereum to post data (not in the provided files). Sources, see external/:
--             primary : DefiLlama op-mainnet  dailyFees - dailyRevenue  (full window, daily)
--             check   : growthepie costs_total_usd                      (public file keeps ~90 days only)
--             attempt : on-chain batcher/proposer via Blockscout       (rate-limited; columns empty if unavailable)
-- net     = gross - l1_cost   ("our share", as the brief defines it)
-- DefiLlama's gross agrees with file 01 within ~2% a month, so mixing its cost with our gross is consistent.
WITH d AS (
    SELECT f.*, a.success_transactions, a.active_addresses,
           c.llama_fees_usd, c.llama_l1_cost_usd, c.gtp_fees_usd, c.gtp_l1_cost_usd, c.onchain_l1_cost_eth
    FROM fees f
    JOIN activity a USING (date)
    LEFT JOIN l1_costs c USING (date)
)
SELECT
    date_trunc('month', date)::DATE                       AS month,
    count(*)                                              AS days,
    sum(fee_paying_txs)                                   AS fee_paying_txs,
    sum(success_transactions)                             AS success_txs,
    avg(active_addresses)                                 AS avg_daily_active_addresses,
    avg(eth_price_usd)                                    AS avg_eth_price_usd,
    sum(execution_fee_eth)                                AS execution_fee_eth,
    sum(l1_data_fee_eth)                                  AS l1_data_fee_eth,
    sum(total_fee_eth)                                    AS gross_fee_eth,
    sum(execution_fee_usd)                                AS execution_fee_usd,
    sum(l1_data_fee_usd)                                  AS l1_data_fee_usd,
    sum(total_fee_usd)                                    AS gross_fee_usd,
    sum(llama_l1_cost_usd)                                AS l1_cost_usd,
    sum(total_fee_usd) - sum(llama_l1_cost_usd)           AS net_usd,
    1 - sum(llama_l1_cost_usd) / sum(total_fee_usd)       AS net_margin,
    sum(l1_data_fee_usd) - sum(llama_l1_cost_usd)         AS l1_data_margin_usd,
    sum(llama_fees_usd)                                   AS check_llama_gross_usd,
    sum(gtp_fees_usd)                                     AS check_gtp_gross_usd,
    sum(gtp_l1_cost_usd)                                  AS check_gtp_l1_cost_usd,
    sum(onchain_l1_cost_eth * eth_price_usd)              AS check_onchain_l1_cost_usd,
    sum(total_fee_usd) / sum(fee_paying_txs)              AS gross_usd_per_tx
FROM d
GROUP BY 1
ORDER BY 1;
