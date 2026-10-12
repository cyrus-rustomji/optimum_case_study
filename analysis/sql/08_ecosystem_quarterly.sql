-- Q2: signals for customer targets beyond the apps that pay gas today (users, builders, stablecoin issuers,
-- bridges, exchanges, liquidity). Quarterly, flows normalised to a 91-day quarter so the partial
-- Q3 2026 (ends Sep 15) compares fairly. Balances (supply, TVL) are quarterly averages of end-of-day values,
-- never sums across days (README rule).
WITH q AS (SELECT DISTINCT date_trunc('quarter', date)::DATE AS qtr FROM fees),
days AS (SELECT date_trunc('quarter', date)::DATE AS qtr, count(*) AS n FROM fees GROUP BY 1),
stab AS (
    SELECT date_trunc('quarter', date)::DATE AS qtr,
           avg(native) AS native_stable_supply_usd, avg(bridged) AS bridged_stable_supply_usd
    FROM (SELECT date,
                 sum(circulating_supply_usd) FILTER (WHERE is_native)     AS native,
                 sum(circulating_supply_usd) FILTER (WHERE NOT is_native) AS bridged
          FROM stables GROUP BY 1)
    GROUP BY 1
),
stab_vol AS (
    SELECT date_trunc('quarter', date)::DATE AS qtr, sum(adjusted_volume_usd) AS stable_adj_volume_usd
    FROM stables GROUP BY 1
),
br AS (  -- aggregators excluded: their volume is already in the bridge they route through (README)
    SELECT date_trunc('quarter', date)::DATE AS qtr,
           sum(usd_volume) FILTER (WHERE direction = 'inbound')  AS bridge_in_usd,
           sum(usd_volume) FILTER (WHERE direction = 'outbound') AS bridge_out_usd
    FROM bridges WHERE bridge_type <> 'bridge_aggregator' GROUP BY 1
),
cx AS (
    SELECT date_trunc('quarter', date)::DATE AS qtr,
           sum(usd_amount_in) AS cex_deposits_usd, sum(usd_amount_out) AS cex_withdrawals_usd
    FROM cex GROUP BY 1
),
tv AS (
    SELECT date_trunc('quarter', date)::DATE AS qtr, avg(t) AS tvl_usd
    FROM (SELECT date, sum(tvl_usd) AS t FROM tvl
          WHERE NOT exclude_from_global_tvl AND NOT has_double_counted_tvl GROUP BY 1)
    GROUP BY 1
),
dx AS (SELECT date_trunc('quarter', date)::DATE AS qtr, sum(total_volume_usd) AS dex_volume_usd FROM dex GROUP BY 1),
na AS (
    SELECT date_trunc('quarter', date)::DATE AS qtr, sum(new_addresses) AS new_addresses,
           avg(returning_addresses) AS avg_daily_returning_addresses
    FROM new_addr GROUP BY 1
),
dp AS (
    SELECT date_trunc('quarter', date)::DATE AS qtr, avg(distinct_contract_deployers) AS avg_daily_deployers,
           sum(new_deployed_contracts) AS contracts_deployed
    FROM deploys GROUP BY 1
)
SELECT q.qtr, days.n AS days,
       stab.native_stable_supply_usd, stab.bridged_stable_supply_usd,
       stab_vol.stable_adj_volume_usd * 91 / days.n AS stable_adj_volume_usd_91d,
       br.bridge_in_usd * 91 / days.n            AS bridge_in_usd_91d,
       br.bridge_out_usd * 91 / days.n           AS bridge_out_usd_91d,
       cx.cex_deposits_usd * 91 / days.n         AS cex_deposits_usd_91d,
       cx.cex_withdrawals_usd * 91 / days.n      AS cex_withdrawals_usd_91d,
       tv.tvl_usd,
       dx.dex_volume_usd * 91 / days.n           AS dex_volume_usd_91d,
       na.new_addresses * 91 / days.n            AS new_addresses_91d,
       na.avg_daily_returning_addresses,
       dp.avg_daily_deployers,
       dp.contracts_deployed * 91 / days.n       AS contracts_deployed_91d
FROM q
JOIN days USING (qtr)
LEFT JOIN stab USING (qtr) LEFT JOIN stab_vol USING (qtr) LEFT JOIN br USING (qtr) LEFT JOIN cx USING (qtr)
LEFT JOIN tv USING (qtr) LEFT JOIN dx USING (qtr) LEFT JOIN na USING (qtr) LEFT JOIN dp USING (qtr)
ORDER BY 1;
