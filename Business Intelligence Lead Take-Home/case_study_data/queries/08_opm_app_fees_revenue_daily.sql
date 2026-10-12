-- OP Mainnet daily app fees and app revenue by protocol, from DefiLlama.
-- Window: 2025-01-01 through 2026-09-15 (inclusive).
-- fee = total fees users paid to the app; revenue = the part the app keeps;
-- holder_revenue = the part paid to the app's token holders. All USD.
-- These are app-level fees. They are separate from the chain (sequencer) fees in dataset 01.
select
    protocol,
    sub_protocol,
    category,
    date::text as date,
    fee        as fee_usd,
    revenue    as revenue_usd,
    holder_revenue as holder_revenue_usd
from lens.fee_daily
where chain = 'op-mainnet'
  and date >= '2025-01-01'
  and date <= '2026-09-15'
order by date, fee desc nulls last
