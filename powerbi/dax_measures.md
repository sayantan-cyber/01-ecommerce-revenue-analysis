# Power BI: star schema, DAX measures and dashboard layout

Load the six CSVs from `data-exports/` into Power BI (Get Data > Text/CSV).

## Model (star schema)

- fact_orders (order grain): order_id, customer_id, date_key, items, order_value,
  freight_total, payment_type, payment_installments, review_score, delivery_days, late_flag
- fact_order_items (item grain): order_id, order_item_id, product_id, seller_id,
  customer_id, date_key, price, freight_value
- dim_customers -> both facts on customer_id
- dim_products -> fact_order_items on product_id
- dim_sellers -> fact_order_items on seller_id
- dim_date -> both facts on date_key (mark dim_date as a Date table)

All relationships single direction, many-to-one from facts to dimensions.

## Core DAX measures

Total Revenue = SUM ( fact_orders[order_value] )

Total Orders = COUNTROWS ( fact_orders )

Avg Order Value = DIVIDE ( [Total Revenue], [Total Orders] )

Revenue MoM % =
VAR prev = CALCULATE ( [Total Revenue], DATEADD ( dim_date[date], -1, MONTH ) )
RETURN DIVIDE ( [Total Revenue] - prev, prev )

Revenue YTD = TOTALYTD ( [Total Revenue], dim_date[date] )

On-time Delivery Rate =
DIVIDE (
    CALCULATE ( [Total Orders], fact_orders[late_flag] = 0 ),
    [Total Orders]
)

Avg Review Score = AVERAGE ( fact_orders[review_score] )

Avg Delivery Days = AVERAGE ( fact_orders[delivery_days] )

Freight % of Revenue =
DIVIDE ( SUM ( fact_orders[freight_total] ), [Total Revenue] )

Credit Card Share % =
DIVIDE (
    CALCULATE ( [Total Revenue], fact_orders[payment_type] = "credit_card" ),
    [Total Revenue]
)

## Dashboard pages

1. Executive overview: revenue trend (line, dim_date[year_month]), Total Revenue,
   Orders, AOV, MoM % cards; revenue by state (filled map on dim_customers[customer_state]).
2. Delivery and satisfaction: on-time rate gauge, avg review by late_flag (bar),
   delivery days distribution, reviews over time.
3. Customers and segments: RFM segment table (dim_customers[segment]), revenue by
   segment, cohort retention matrix (from cohort_retention_pct.csv if loaded separately).
4. Products and sellers: top categories (bar), freight % by state, seller leaderboard.

Use dim_date for every time axis so time-intelligence measures work.
