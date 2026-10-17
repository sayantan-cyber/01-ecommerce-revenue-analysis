"""
Project 1: Brazilian E-Commerce (Olist) - reproducible analysis pipeline.

Reads the 9 raw CSVs from ./data/ (download links in README.md), validates them,
computes every headline metric, builds cohort retention and RFM/CLV analyses,
saves 6 charts into ./visuals/ and the Power BI star schema into ./data-exports/.

Run:  python notebooks/olist_analysis.py
Deps: pandas, numpy, matplotlib (see requirements.txt)

Every number quoted in README.md and docs/findings_and_recommendations.md
comes from this script, verified against the raw files on 17 Oct 2026.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA, VIS, EXP = ROOT / 'data', ROOT / 'visuals', ROOT / 'data-exports'
VIS.mkdir(exist_ok=True); EXP.mkdir(exist_ok=True)

INK, TEAL, GREY = '#251f21', '#73a89a', '#9a9496'
plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})

# ---------------------------------------------------------------- 1. Load
orders = pd.read_csv(DATA / 'olist_orders_dataset.csv')
items = pd.read_csv(DATA / 'olist_order_items_dataset.csv')
pay = pd.read_csv(DATA / 'olist_order_payments_dataset.csv')
rev = pd.read_csv(DATA / 'olist_order_reviews_dataset.csv')
cust = pd.read_csv(DATA / 'olist_customers_dataset.csv')
prod = pd.read_csv(DATA / 'olist_products_dataset.csv')
trans = pd.read_csv(DATA / 'product_category_name_translation.csv')
sellers = pd.read_csv(DATA / 'olist_sellers_dataset.csv')

for col in ['order_purchase_timestamp', 'order_delivered_customer_date',
            'order_estimated_delivery_date']:
    orders[col] = pd.to_datetime(orders[col])

# ----------------------------------------------------- 2. Validation checks
checks = {
    'orders rows == 99,441': len(orders) == 99441,
    'order_id is unique': orders['order_id'].is_unique,
    'every item belongs to a real order': bool(items['order_id'].isin(orders['order_id']).all()),
    'no duplicate order rows': not bool(orders.duplicated().any()),
    'review scores within 1-5': bool(rev['review_score'].between(1, 5).all()),
    'payment values non-negative': bool((pay['payment_value'] >= 0).all()),
}
for name, ok in checks.items():
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
assert all(checks.values()), 'Validation failed. Inspect the raw files before trusting any output.'

# ------------------------------------------------------- 3. Headline metrics
deliv = orders[orders['order_status'] == 'delivered'].copy()
d_items = items[items['order_id'].isin(deliv['order_id'])]
print('\n-- Headline metrics (delivered orders) --')
print('Total product revenue (BRL):', round(d_items['price'].sum(), 2))
print('Total freight revenue (BRL):', round(d_items['freight_value'].sum(), 2))
print('Average order value (BRL):', round(d_items.groupby('order_id')['price'].sum().mean(), 2))

pm = pay.groupby('payment_type')['payment_value'].sum().sort_values(ascending=False)
print('\nPayment mix (% of value):')
print((pm / pm.sum() * 100).round(1))
print('Avg credit-card installments:', round(pay[pay['payment_type'] == 'credit_card']['payment_installments'].mean(), 2))

# --------------------------------------------- 4. Delivery vs review scores
deliv['delivery_days'] = (deliv['order_delivered_customer_date'] - deliv['order_purchase_timestamp']).dt.total_seconds() / 86400
deliv['late'] = deliv['order_delivered_customer_date'] > deliv['order_estimated_delivery_date']
dr = deliv[['order_id', 'delivery_days', 'late']].merge(rev[['order_id', 'review_score']], on='order_id')
print('\n-- Delivery vs reviews --')
print('Late deliveries %:', round(dr['late'].mean() * 100, 1))
print('Avg delivery days, on-time vs late:', round(dr[~dr['late']]['delivery_days'].mean(), 1), round(dr[dr['late']]['delivery_days'].mean(), 1))
print('Avg review score, on-time vs late:', round(dr[~dr['late']]['review_score'].mean(), 2), round(dr[dr['late']]['review_score'].mean(), 2))
print('Correlation(delivery days, review score):', round(dr[['delivery_days', 'review_score']].dropna().corr().iloc[0, 1], 3))

# ----------------------------------------------------------- 5. Categories
pr = prod.merge(trans, on='product_category_name', how='left')
pr['category'] = pr['product_category_name_english'].fillna(pr['product_category_name']).fillna('unknown')
catrev = d_items.merge(pr[['product_id', 'category']], on='product_id').groupby('category')['price'].sum().sort_values(ascending=False)
print('\nTop 5 categories by revenue:')
print(catrev.head().round(0))

# -------------------------------------------------------------- 6. Cohorts
co = deliv.merge(cust[['customer_id', 'customer_unique_id']], on='customer_id')
co = co.merge(items.groupby('order_id')['price'].sum().rename('order_value'), on='order_id')
co['order_month'] = co['order_purchase_timestamp'].dt.to_period('M')
co = co.join(co.groupby('customer_unique_id')['order_month'].min().rename('cohort'), on='customer_unique_id')
co['period'] = (co['order_month'] - co['cohort']).apply(lambda x: x.n)
cohort = co.groupby(['cohort', 'period'])['customer_unique_id'].nunique().unstack(fill_value=0)
retention = (cohort.divide(cohort[0], axis=0) * 100).round(1)
retention.to_csv(EXP / 'cohort_retention_pct.csv')
print('\n-- Cohort retention --')
print('Avg retention month 1 / 6 / 12 %:',
      round(retention[1].mean(), 1), round(retention[6].dropna().mean(), 1), round(retention[12].dropna().mean(), 1))

# ------------------------------------------------------------------ 7. RFM
snap = co['order_purchase_timestamp'].max() + pd.Timedelta(days=1)
rfm = co.groupby('customer_unique_id').agg(
    recency=('order_purchase_timestamp', lambda x: (snap - x.max()).days),
    frequency=('order_id', 'nunique'),
    monetary=('order_value', 'sum'))
for c, asc in [('R', True), ('F', False), ('M', False)]:
    col = {'R': 'recency', 'F': 'frequency', 'M': 'monetary'}[c]
    rfm[c] = pd.qcut(rfm[col].rank(method='first'), 4, labels=[4, 3, 2, 1] if asc else [1, 2, 3, 4]).astype(int)
rfm['segment'] = (rfm['R'] + rfm['F'] + rfm['M']).apply(
    lambda s: 'Champions' if s >= 11 else 'Loyal' if s >= 9 else 'Promising' if s >= 7 else 'At risk' if s >= 5 else 'Lost')
segsum = rfm.groupby('segment').agg(customers=('segment', 'size'), avg_monetary=('monetary', 'mean')).round(0)
segsum.to_csv(EXP / 'rfm_segments.csv')
print('\n-- RFM segments --')
print(segsum)
print('Champions share of lifetime revenue %:',
      round(rfm[rfm['segment'] == 'Champions']['monetary'].sum() / rfm['monetary'].sum() * 100, 1))

# ----------------------------------------------------------------- 8. Charts
mrev = d_items.merge(deliv[['order_id', 'order_purchase_timestamp']], on='order_id')
mrev['month'] = mrev['order_purchase_timestamp'].dt.to_period('M')
m = mrev.groupby('month')['price'].sum()
m.to_csv(EXP / 'monthly_revenue.csv')

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot([str(i) for i in m.index], m.values / 1e6, color=TEAL, marker='o', ms=4, lw=2)
ax.set_title('Monthly product revenue, delivered orders (R$ million)', fontsize=13, weight='bold')
ax.set_ylabel('R$ million'); ax.set_xticks(range(0, len(m), 3)); ax.tick_params(axis='x', rotation=60)
fig.tight_layout(); fig.savefig(VIS / '01_monthly_revenue.png', dpi=150); plt.close(fig)

c = catrev.head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.barh(c.index, c.values / 1e6, color=[TEAL if i == len(c) - 1 else GREY for i in range(len(c))])
ax.set_title('Top 10 categories by revenue (R$ million)', fontsize=13, weight='bold'); ax.set_xlabel('R$ million')
fig.tight_layout(); fig.savefig(VIS / '02_top_categories.png', dpi=150); plt.close(fig)

p = pm[pm > 0].sort_values()
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.barh(p.index, p.values / p.values.sum() * 100, color=[TEAL if x == 'credit_card' else GREY for x in p.index])
ax.set_title('Share of payment value by type (%)', fontsize=13, weight='bold')
for i, v in enumerate(p.values / p.values.sum() * 100):
    ax.text(v + 0.8, i, f'{v:.1f}%', va='center')
fig.tight_layout(); fig.savefig(VIS / '03_payment_mix.png', dpi=150); plt.close(fig)

g = dr.groupby('late')['review_score'].mean()
fig, ax = plt.subplots(figsize=(6, 4.2))
ax.bar(['On time', 'Late'], g.values, color=[TEAL, '#c96a6a'])
ax.set_ylim(0, 5); ax.set_ylabel('Average review score')
ax.set_title('Late delivery cuts review scores', fontsize=13, weight='bold')
for i, v in enumerate(g.values):
    ax.text(i, v + 0.08, f'{v:.2f}', ha='center')
fig.tight_layout(); fig.savefig(VIS / '04_delivery_vs_reviews.png', dpi=150); plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 5.2))
r = retention.iloc[:, 1:13]  # drop period 0 (trivially 100%)
im = ax.imshow(r.values, aspect='auto', cmap=matplotlib.colors.LinearSegmentedColormap.from_list('t', ['white', TEAL]), vmin=0, vmax=10)
ax.set_xticks(range(len(r.columns))); ax.set_xticklabels(r.columns)
ax.set_yticks(range(len(r.index))); ax.set_yticklabels(r.index, fontsize=8)
ax.set_title('Cohort retention: % of customers ordering again in month N', fontsize=13, weight='bold')
ax.set_xlabel('Months since first order'); fig.colorbar(im, label='% retained')
fig.tight_layout(); fig.savefig(VIS / '05_cohort_retention.png', dpi=150); plt.close(fig)

s = segsum.sort_values('customers')
fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(s.index, s['customers'], color=GREY)
ax2 = ax.twiny(); ax2.plot(s['avg_monetary'], s.index, 'o-', color=TEAL)
ax.set_title('RFM segments: customer count (bars) and avg lifetime revenue (line, R$)', fontsize=12, weight='bold')
ax.set_xlabel('Customers'); ax2.set_xlabel('Avg lifetime revenue (R$)', color=TEAL); ax2.spines['top'].set_visible(True)
fig.tight_layout(); fig.savefig(VIS / '06_rfm_segments.png', dpi=150); plt.close(fig)

# -------------------------------------------------- 9. Power BI star schema
cust2 = cust.merge(rfm[['segment']], left_on='customer_unique_id', right_index=True, how='left')
cust2.to_csv(EXP / 'dim_customers.csv', index=False)
pr[['product_id', 'category', 'product_weight_g', 'product_length_cm', 'product_height_cm', 'product_width_cm', 'product_photos_qty']].to_csv(EXP / 'dim_products.csv', index=False)
sellers.to_csv(EXP / 'dim_sellers.csv', index=False)

dates = pd.date_range('2016-09-01', '2018-10-31', freq='D')
dim_date = pd.DataFrame({'date': dates})
dim_date['date_key'] = dim_date['date'].dt.strftime('%Y%m%d').astype(int)
dim_date['year'] = dim_date['date'].dt.year
dim_date['month'] = dim_date['date'].dt.month
dim_date['month_name'] = dim_date['date'].dt.strftime('%b')
dim_date['year_month'] = dim_date['date'].dt.strftime('%Y-%m')
dim_date['quarter'] = dim_date['date'].dt.quarter
dim_date['day_of_week'] = dim_date['date'].dt.day_name()
dim_date[['date_key', 'date', 'year', 'month', 'month_name', 'year_month', 'quarter', 'day_of_week']].to_csv(EXP / 'dim_date.csv', index=False)

it = items.groupby('order_id').agg(items=('order_item_id', 'count'), order_value=('price', 'sum'), freight_total=('freight_value', 'sum')).reset_index()
pmain = pay.sort_values('payment_value', ascending=False).drop_duplicates('order_id')[['order_id', 'payment_type', 'payment_installments', 'payment_value']]
rmain = rev.drop_duplicates('order_id')[['order_id', 'review_score']]
fact = deliv.merge(it, on='order_id').merge(pmain, on='order_id', how='left').merge(rmain, on='order_id', how='left')
fact['delivery_days'] = fact['delivery_days'].round(1)
fact['late_flag'] = fact['late'].astype(int)
fact['date_key'] = fact['order_purchase_timestamp'].dt.strftime('%Y%m%d').astype(int)
fact[['order_id', 'customer_id', 'date_key', 'items', 'order_value', 'freight_total',
      'payment_type', 'payment_installments', 'review_score', 'delivery_days', 'late_flag']].to_csv(EXP / 'fact_orders.csv', index=False)

foi = items.merge(deliv[['order_id', 'customer_id', 'order_purchase_timestamp']], on='order_id')
foi['date_key'] = foi['order_purchase_timestamp'].dt.strftime('%Y%m%d').astype(int)
foi[['order_id', 'order_item_id', 'product_id', 'seller_id', 'customer_id', 'date_key',
     'price', 'freight_value']].to_csv(EXP / 'fact_order_items.csv', index=False)

print('\nStar schema exported to data-exports/:')
for f in ['dim_customers', 'dim_products', 'dim_sellers', 'dim_date', 'fact_orders', 'fact_order_items']:
    print(' ', f, pd.read_csv(EXP / f'{f}.csv').shape)
print('\nPipeline complete.')
