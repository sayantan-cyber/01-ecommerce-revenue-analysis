# Findings and business recommendations

Analysis of 99,441 real Olist orders (Sep 2016 - Oct 2018), 96,478 of them delivered.
Every number below is produced by `notebooks/olist_analysis.py` from the raw files.

## What the data says

1. **Revenue grew steadily to a peak of R$ 987,765 in Nov 2017 (Black Friday month).**
   Total product revenue on delivered orders: R$ 13.22 M, plus R$ 2.20 M freight.
   Average order value: R$ 137.04.

2. **Late delivery is the single biggest satisfaction killer.** Only 8.0% of orders
   arrive late, but those orders average a 2.57 review score against 4.29 for on-time
   orders. Late orders also take 31.4 days on average vs 10.9 for on-time ones.
   Correlation between delivery days and review score: -0.334.

3. **Customers almost never come back.** Month-1 cohort retention averages 4.7%,
   falling to 0.2% by month 6. Only 3.0% of customers ever place a second order.
   This is a one-purchase marketplace, not a loyalty business yet.

4. **Champions are few but valuable.** The top RFM segment (6,205 customers, 6.4% of
   the base) accounts for 14.3% of lifetime revenue and spends R$ 306 on average vs
   R$ 142 overall.

5. **Credit cards carry the business.** 78.3% of payment value is credit card, with an
   average of 3.51 installments. Boleto (bank slip) is second at 17.9%.

6. **Freight is a regional tax.** In remote states like Roraima and Maranhao, freight
   is 24-28% of the product price, against far lower shares near Sao Paulo, where most
   sellers sit.

## Recommendations

1. **Fix the late-delivery tail before anything else.** An 8% late share sounds small,
   but it produces the worst reviews on the platform. Set stricter shipping-limit
   enforcement for sellers with chronic lateness, and flag orders whose estimated
   delivery date is already unrealistic at purchase time.

2. **Build a repeat-purchase program.** With 97% of customers never ordering again,
   even moving repeat rate from 3% to 5% grows revenue without any new acquisition.
   A post-delivery voucher for a second purchase is the cheapest lever.

3. **Protect and study the Champions.** 6.4% of customers drive 14.3% of revenue.
   Identify the categories and sellers they buy from and defend that experience.

4. **Review freight pricing in remote states.** A 24-28% freight share likely
   suppresses demand there. Subsidized freight thresholds are worth an A/B test.

## Limitations

- Data covers 2016-2018 only; Brazilian e-commerce has changed since.
- Reviews are missing for some delivered orders, so review-based findings cover the
  ~99k orders that have one.
- RFM segments use quartile ranks; SQL NTILE and pandas qcut handle ties differently,
  so exact segment sizes can differ slightly between the SQL and Python versions.
- Customer identity relies on `customer_unique_id`; address-level duplicates may split
  a real person into two "customers", which can understate repeat behavior.
