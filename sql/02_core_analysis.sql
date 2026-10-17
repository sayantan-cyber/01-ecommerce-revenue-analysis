-- Project 1 core analysis (MySQL 8: CTEs and window functions)
USE olist_analytics;

-- Q1. Monthly revenue trend with running total and MoM growth
WITH monthly AS (
    SELECT DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS month,
           SUM(i.price) AS revenue
    FROM orders o
    JOIN order_items i ON i.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY 1
)
SELECT month,
       revenue,
       SUM(revenue) OVER (ORDER BY month) AS running_revenue,
       ROUND(100 * (revenue / LAG(revenue) OVER (ORDER BY month) - 1), 1) AS mom_growth_pct
FROM monthly
ORDER BY month;

-- Q2. Top categories by revenue with rank and share
WITH cat AS (
    SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
           SUM(i.price) AS revenue
    FROM order_items i
    JOIN products p ON p.product_id = i.product_id
    LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
    GROUP BY 1
)
SELECT category, revenue,
       RANK() OVER (ORDER BY revenue DESC) AS revenue_rank,
       ROUND(100 * revenue / SUM(revenue) OVER (), 2) AS revenue_share_pct
FROM cat
ORDER BY revenue DESC
LIMIT 10;

-- Q3. Delivery performance vs review score
SELECT CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
            THEN 'late' ELSE 'on_time' END AS delivery_flag,
       COUNT(*) AS orders,
       ROUND(AVG(r.review_score), 2) AS avg_review_score,
       ROUND(AVG(TIMESTAMPDIFF(HOUR, o.order_purchase_timestamp,
             o.order_delivered_customer_date)) / 24, 1) AS avg_delivery_days
FROM orders o
JOIN order_reviews r ON r.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY 1;

-- Q4. Cohort retention: share of each first-purchase month cohort ordering again in month N
WITH firsts AS (
    SELECT c.customer_unique_id,
           DATE_FORMAT(MIN(o.order_purchase_timestamp), '%Y-%m-01') AS cohort_month
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY 1
),
activity AS (
    SELECT DISTINCT c.customer_unique_id,
           DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m-01') AS active_month
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
)
SELECT f.cohort_month,
       COUNT(*) AS cohort_size,
       TIMESTAMPDIFF(MONTH, f.cohort_month, a.active_month) AS months_since_first,
       COUNT(DISTINCT a.customer_unique_id) AS active_customers,
       ROUND(100 * COUNT(DISTINCT a.customer_unique_id) / COUNT(*), 2) AS retention_pct
FROM firsts f
JOIN activity a ON a.customer_unique_id = f.customer_unique_id
GROUP BY 1, 3
ORDER BY 1, 3;

-- Q5. RFM segmentation (recency, frequency, monetary quintiles)
WITH rfm_base AS (
    SELECT c.customer_unique_id,
           DATEDIFF((SELECT MAX(order_purchase_timestamp) FROM orders) + INTERVAL 1 DAY,
                    MAX(o.order_purchase_timestamp)) AS recency_days,
           COUNT(DISTINCT o.order_id) AS frequency,
           SUM(oi.price) AS monetary
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY 1
),
scored AS (
    SELECT *,
           NTILE(4) OVER (ORDER BY recency_days DESC) AS r,
           NTILE(4) OVER (ORDER BY frequency) AS f,
           NTILE(4) OVER (ORDER BY monetary) AS m
    FROM rfm_base
)
SELECT CASE WHEN r + f + m >= 11 THEN 'Champions'
            WHEN r + f + m >= 9  THEN 'Loyal'
            WHEN r + f + m >= 7  THEN 'Promising'
            WHEN r + f + m >= 5  THEN 'At risk'
            ELSE 'Lost' END AS segment,
       COUNT(*) AS customers,
       ROUND(AVG(monetary), 0) AS avg_lifetime_revenue
FROM scored
GROUP BY 1
ORDER BY avg_lifetime_revenue DESC;

-- Q6. Payment mix and installments
SELECT payment_type,
       COUNT(*) AS payments,
       ROUND(100 * SUM(payment_value) / SUM(SUM(payment_value)) OVER (), 1) AS value_share_pct,
       ROUND(AVG(payment_installments), 2) AS avg_installments
FROM order_payments
GROUP BY payment_type
ORDER BY value_share_pct DESC;

-- Q7. Freight analysis: average freight share of item price by customer state
SELECT c.customer_state,
       COUNT(*) AS items,
       ROUND(AVG(i.freight_value), 2) AS avg_freight,
       ROUND(100 * SUM(i.freight_value) / SUM(i.price), 1) AS freight_pct_of_price
FROM order_items i
JOIN orders o ON o.order_id = i.order_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered'
GROUP BY 1
ORDER BY freight_pct_of_price DESC;

-- Q8. Query optimization demo: run before and after adding the index, compare EXPLAIN
-- EXPLAIN ANALYZE
-- SELECT o.order_id FROM orders o WHERE o.order_status = 'delivered'
--   AND o.order_purchase_timestamp >= '2018-01-01';
-- The schema already ships the two indexes that matter (order_status, order_purchase_timestamp).
-- Drop them, re-run EXPLAIN, and compare rows examined.
