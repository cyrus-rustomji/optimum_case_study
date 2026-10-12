-- OP Mainnet daily TVL (total value locked, the USD value of assets deposited in each app) by protocol,
-- from DefiLlama. Window: 2025-01-01 through 2026-09-15 (inclusive).
-- tvl_component = 'base' only (standard deposits; excludes borrowed, staking, pool2, treasury, vesting).
-- To match DefiLlama's headline chain TVL, keep rows where exclude_from_global_tvl = false
-- AND has_double_counted_tvl = false. Summing all rows double-counts.
select
    protocol,
    category,
    date::text as date,
    sum(tvl)   as tvl_usd,
    bool_or(exclude_from_global_tvl) as exclude_from_global_tvl,
    bool_or(has_double_counted_tvl)  as has_double_counted_tvl
from lens.tvl_daily
where chain = 'op-mainnet'
  and tvl_component = 'base'
  and date >= '2025-01-01'
  and date <= '2026-09-15'
group by protocol, category, date
order by date, tvl_usd desc nulls last
