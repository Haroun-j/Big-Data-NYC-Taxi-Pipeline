-- SQL behind the four Metabase questions (docs/screenshots/metabase_dashboard.png).
-- The first two were built with the visual editor; this is the equivalent SQL.
-- The last two are native SQL questions, because Metabase auto-binned the
-- hour into 3-hour buckets and I wanted the 24 individual hours.

-- 1. Daily trips over 2023
SELECT DATE(d.full_timestamp) AS day,
       COUNT(*)              AS trips
FROM fact_trip f
JOIN dim_datetime d ON f.pickup_datetime_id = d.datetime_id
GROUP BY day
ORDER BY day;

-- 2. Trips by pickup borough
SELECT z.borough,
       COUNT(*) AS trips
FROM fact_trip f
JOIN dim_zone z ON f.pickup_zone_id = z.zone_id
GROUP BY z.borough
ORDER BY trips DESC;

-- 3. Average fare by hour of pickup (fares above 200 are a handful of
--    negotiated / erroneous rows that pull the average around)
SELECT d.hour,
       AVG(f.fare_amount)::numeric(10, 2) AS avg_fare
FROM fact_trip f
JOIN dim_datetime d ON f.pickup_datetime_id = d.datetime_id
WHERE f.fare_amount > 0
  AND f.fare_amount < 200
GROUP BY d.hour
ORDER BY d.hour;

-- 4. Payment type distribution
SELECT p.payment_label,
       COUNT(*) AS trips,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM fact_trip f
JOIN dim_payment_type p ON f.payment_type_id = p.payment_type_id
GROUP BY p.payment_label
ORDER BY trips DESC;
