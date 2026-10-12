-- Q2: customer churn / retention, at the address level (the grain file 06 is cut at).
-- "Paying customer in month m" = an individually-tracked address that sent >= $10 of fees in month m
-- ($10 keeps out addresses that got one stray tx; the README's inclusion rule is per-month volume, not fees).
-- Logo retention: of addresses paying in month m, share still paying in month m+3.
-- Net revenue retention (NRR): fees in m+3 from the month-m cohort / their fees in month m.
-- Months: complete months only (Sep 2026 is partial, so m+3 is capped at Aug 2026).
WITH m AS (
    SELECT to_address, date_trunc('month', date)::DATE AS month, sum(total_fee_usd) AS usd
    FROM contract_activity
    WHERE to_address <> 'other' AND date < DATE '2026-09-01'
    GROUP BY ALL
    HAVING sum(total_fee_usd) >= 10
),
pairs AS (
    SELECT a.month, a.to_address, a.usd AS usd0, b.usd AS usd3
    FROM m a LEFT JOIN m b
      ON b.to_address = a.to_address AND b.month = a.month + INTERVAL 3 MONTH
    WHERE a.month + INTERVAL 3 MONTH <= DATE '2026-08-01'
),
first_month AS (SELECT to_address, min(month) AS cohort FROM m GROUP BY 1)
SELECT p.month,
       count(*)                                         AS paying_addresses,
       count(*) FILTER (WHERE f.cohort = p.month)        AS new_paying_addresses,
       avg((usd3 IS NOT NULL)::INT)                      AS logo_retention_3m,
       sum(coalesce(usd3, 0)) / sum(usd0)                AS nrr_3m,
       sum(usd0)                                         AS cohort_fees_usd
FROM pairs p JOIN first_month f USING (to_address)
GROUP BY 1
ORDER BY 1;
