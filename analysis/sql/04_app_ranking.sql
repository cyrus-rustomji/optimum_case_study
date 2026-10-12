-- Q2: customers of OP Mainnet = whoever's transactions pay the sequencer.
-- Grain: app (named) or address (unnamed), last 12 months. Requires address_dim (03).
-- A tx's fee is paid by the sender; file 06 assigns it to the destination. So "app X paid" means
-- "users/bots calling app X paid" - which is how blockspace demand is attributed to customers.
WITH w AS (
    SELECT c.*, d.segment,
           coalesce(d.app, 'unnamed ' || left(c.to_address, 10)) AS customer
    FROM contract_activity c
    JOIN address_dim d ON d.address = c.to_address
    WHERE c.date BETWEEN getvariable('l12m_start') AND getvariable('l12m_end')
),
tot AS (SELECT sum(total_fee_usd) AS t FROM w),
cust AS (
    SELECT customer, min(segment) AS segment,  -- an app maps to one segment today; min() keeps it deterministic
           count(DISTINCT to_address)                 AS addresses,
           count(DISTINCT date)                       AS active_days,
           sum(txs)                                   AS txs,
           sum(total_fee_eth)                         AS fee_eth,
           sum(total_fee_usd)                         AS fee_usd,
           sum(total_fee_usd) / sum(txs) * 1000       AS usd_per_1k_tx,
           sum(txs) / nullif(sum(distinct_senders), 0) AS txs_per_sender_day,
           -- how "spiky" a customer is: share of its 12m fees paid on its 10 biggest days
           NULL::DOUBLE                               AS top10_day_share
    FROM w GROUP BY 1
),
spiky AS (
    SELECT customer, sum(usd) AS top10 FROM (
        SELECT customer, date, sum(total_fee_usd) AS usd,
               row_number() OVER (PARTITION BY customer ORDER BY sum(total_fee_usd) DESC, date) AS rn
        FROM w GROUP BY 1, 2) WHERE rn <= 10 GROUP BY 1
)
SELECT c.* EXCLUDE (top10_day_share),
       s.top10 / c.fee_usd                                   AS top10_day_share,
       c.fee_usd / tot.t                                     AS share_of_gross,
       sum(c.fee_usd) OVER (ORDER BY c.fee_usd DESC, c.customer ROWS UNBOUNDED PRECEDING) / tot.t AS cum_share,
       row_number() OVER (ORDER BY c.fee_usd DESC, c.customer) AS rank
FROM cust c JOIN spiky s USING (customer), tot
-- customer is the deterministic tiebreak (23 customers tie at $0)
ORDER BY c.fee_usd DESC, c.customer;
