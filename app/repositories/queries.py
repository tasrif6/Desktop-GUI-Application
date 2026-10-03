ENTERED_STOCK = """
select P.sales_channel_code,p.party_id PARTY_ID,TRIM(p.Party_Name) Party_Name,
p.party_number, sd.item_code, sd."model" ,sum(sd.qty) Qty
from iceberg.weapp_prod.weapp_prod___distributor_stock SM
inner join iceberg.weapp_prod.weapp_prod___distributor_product_stock SD on SM.id=SD.stock_id
inner join iceberg.weapp_prod.weapp_prod___user_ebs p on p.party_id=SM.Party_id
where date(sm.updated_at) >= date('{start}') and date(sm.updated_at) < date('{end}')
and sd.item_code not in ({excluded_items})
{party_filter}
group by p.sales_channel_code,p.party_id,p.Party_Name,sd.item_code,sd."model",p.party_number
"""

PARTY_LIFTING = """
select c.party_id PARTY_ID,p.product,cast(p.item_code as int) item_code,p."model",
sum(d.ship_qty) Ship_Qty,sum(d.sales_amount) Amount,
coalesce(sum(d.sales_amount)/nullif(sum(d.ship_qty),0),0) avg_rate
from iceberg.dwh_sales.net_order_report_day_wise d
inner join iceberg.dwh_sales.dim_customer c on d.cust_account_id=c.cust_account_id
inner join iceberg.dwh_sales.dim_product p
 on d.inv_org_id=p.inv_org_id and d.inv_item_id=p.inventory_item_id
where c.party_id in (
 select party_id from iceberg.weapp_prod.weapp_prod___distributor_stock sm
 where date(sm.updated_at)>=date('{start}') and date(sm.updated_at)<date('{end}')
)
and p.product not in ('AIRCONDITIONER-OUTDOOR')
and d.a_date between date_add('year',-4,date('{calc_end}')) and date('{calc_end}')
{party_filter}
group by c.party_id,cast(p.item_code as int),p."model",p.product
having sum(d.sales_amount)>0 and sum(d.ship_qty)>0
"""

PARTY_RECEIVABLE_TRINO = """
SELECT party_id PARTY_ID,
round(sum(coalesce(l.dr_amount,0)-coalesce(l.cr_amount,0)),0) Balance
FROM iceberg.dwh_sales.fact_customer_dtl_ledger l
WHERE ledger_id in (2021)
AND date(gl_date)<=date('{calc_end}')
AND party_id IN (
      SELECT party_id
      FROM iceberg.weapp_prod.weapp_prod___distributor_stock
  )
{party_filter}
GROUP BY party_id
"""

PARTY_RECEIVABLE_ORACLE = """
SELECT PARTY_ID,
NVL((SUM(NVL(dr_amount,0))-SUM(NVL(cr_amount,0))),0) Balance
FROM apps.xx_ar_customer_dtl_ledger dl
WHERE 1 = 1 dl.LEDGER_ID IN (2021)
AND trunc(GL_DATE) <= '{calc_end_oracle}'
{party_filter}
GROUP BY PARTY_ID
"""

PARTY_INFO = """
SELECT CUST_ACCT.sales_channel_code,PARTY.PARTY_ID,
PARTY.party_number,ACCT_USE.CUST_ACCOUNT_ID customer_id,
SITE_USE.location,PARTY.party_name,CUST_ACCT.customer_class_code
FROM iceberg.ebs_12_2_5.ar___hz_parties PARTY
inner join iceberg.ebs_12_2_5.ar___hz_cust_accounts CUST_ACCT
 on PARTY.PARTY_ID=CUST_ACCT.PARTY_ID
inner join iceberg.ebs_12_2_5.ar___hz_cust_acct_sites_all ACCT_USE
 on CUST_ACCT.CUST_ACCOUNT_ID=ACCT_USE.CUST_ACCOUNT_ID
inner join iceberg.ebs_12_2_5.ar___hz_cust_site_uses_all SITE_USE
 on SITE_USE.CUST_ACCT_SITE_ID=ACCT_USE.CUST_ACCT_SITE_ID
inner join iceberg.ebs_12_2_5.ar___hz_party_sites PS
 on ACCT_USE.PARTY_SITE_ID=PS.PARTY_SITE_ID
inner join iceberg.ebs_12_2_5.ar___hz_locations LOC
 on PS.LOCATION_ID=LOC.LOCATION_ID
inner join iceberg.ebs_12_2_5.apps___hr_operating_units Org
 on acct_use.org_id=org.organization_id
where CUST_ACCT.SALES_CHANNEL_CODE in ('WALTON DISTRIBUTOR','MARCEL DISTRIBUTOR')
AND SITE_USE.SITE_USE_CODE='BILL_TO'
AND SITE_USE.PRIMARY_FLAG='Y'
AND CUST_ACCT.ACCOUNT_NAME not like '%WITP%'
AND CUST_ACCT.ACCOUNT_NAME not like '%CELLCOM%'
AND CUST_ACCT.ACCOUNT_NAME not like '%SAP%'
AND CUST_ACCT.CUSTOMER_CLASS_CODE IN
 ('EXCLUSIVE','EXCLUSIVE-N','EXCLUSIVE-D','EXCLUSIVE-C','FRANCHISEE GOLD',
  'DEVELOPING PARTY','DEVELOPING PARTY-N','PRE-RECOVERY','PRE-RECOVERY-N','DEVELOPING PARTY-B')
AND PARTY.STATUS='A' AND CUST_ACCT.STATUS='A' AND SITE_USE.STATUS='A'
and SITE_USE.location='Electronics'
AND LOC.ADDRESS_LINES_PHONETIC is not null
AND PARTY.party_id not in (103895)
GROUP BY CUST_ACCT.sales_channel_code,PARTY.PARTY_ID,PARTY.party_number,
ACCT_USE.CUST_ACCOUNT_ID,SITE_USE.location,PARTY.party_name,CUST_ACCT.customer_class_code
"""

PARTY_INFO_FILTERED = PARTY_INFO.replace(
  "AND PARTY.party_id not in (103895)",
  "AND PARTY.party_id not in (103895)\n{party_filter}"
)

CURRENT_RECEIVING = """
select c.party_id PARTY_ID,p.product, cast(p.item_code as int) item_code,p.model,
sum(d.ship_qty) CURR_RCV_QTY,sum(d.sales_amount) CURR_RCV_VAL,
coalesce(sum(d.sales_amount)/sum(d.ship_qty),0) avg_rate
from iceberg.dwh_sales.net_order_report_day_wise d
inner join iceberg.dwh_sales.dim_customer c on d.cust_account_id = c.cust_account_id
inner join iceberg.dwh_sales.dim_product p on d.inv_org_id = p.inv_org_id and d.inv_item_id = p.inventory_item_id 
WHERE date(d.a_date)>=date('{start}') AND date(d.a_date)<date('{end}')
group by c.party_id,cast(p.item_code as int),p.model,p.product
having sum(d.sales_amount)>0 and sum(d.ship_qty)>0
"""

PREVIOUS_STOCK = """
SELECT t.PARTY_ID,
sum(t.CALCULATED_STOCK_VALUE) PREV_CALCULATED_STOCK_VALUE,
sum(t.previous_stock_qty) PREV_RCV,
sum(t.amount) PREV_USER_STOCK_VALUE,
sum(t.amount)*0.02 PREV_USER_STOCK_VALUE_2PER
FROM iceberg.reg.dbo___tblpartyinventoryawaz t
WHERE date(t.STOCK_DATE)=date('{prev_end}')
GROUP BY t.PARTY_ID
"""
