import pandas as pd
import time
from app.repositories.queries import *
from app.utils.dates import oracle_date
from app.config.settings import EXCLUDED_ITEM_CODES, EXCLUDED_PRODUCTS
from app.repositories.db import DatabaseManager

class DataService:
    def __init__(self, db: DatabaseManager, progress=None):
        self.db=db
        self.progress=progress or (lambda msg: None)

    def _q(self, template, **kw):
        return template.format(
            excluded_items=",".join(map(str,EXCLUDED_ITEM_CODES)),
            excluded_products=",".join("'" + x.replace("'","''") + "'" for x in EXCLUDED_PRODUCTS),
            **kw
        )

    def fetch_entered_stock(self,cfg):
        self.progress("Fetching EnteredStock from Data Lake")
        party_filter = self._party_filter(cfg, "p.sales_channel_code", "p.party_id")
        with self.db.connect_trino() as con:
            return pd.read_sql(self._q(ENTERED_STOCK,start=cfg.stock_entry_start.isoformat(),end=cfg.next_month_start.isoformat(),party_filter=party_filter),con)

    def fetch_party_lifting(self,cfg):
        self.progress("Fetching PartyLefting from net_order_report_day_wise")
        print(f"[PartyLifting] FETCH START channel={cfg.sales_channel}, start={cfg.stock_entry_start}, end={cfg.next_month_start}", flush=True)
        fetch_start = time.perf_counter()
        party_filter = self._party_filter(cfg, "c.sales_channel_code", "c.party_id")
        print(f"[PartyLifting] query filter={party_filter or '<none>'}", flush=True)
        with self.db.connect_trino() as con:
            print("[PartyLifting] SQL read START", flush=True)
            df=pd.read_sql(self._q(PARTY_LIFTING,start=cfg.stock_entry_start.isoformat(),end=cfg.next_month_start.isoformat(),calc_end=cfg.stock_start.replace(day=__import__('calendar').monthrange(cfg.stock_year,cfg.stock_month)[1]).isoformat(),party_filter=party_filter),con)
        print(f"[PartyLifting] SQL read DONE in {time.perf_counter() - fetch_start:.2f}s; rows={len(df):,}, columns={list(df.columns)}", flush=True)
        return df

    @staticmethod
    def _party_filter(cfg, channel_column, party_column):
        if cfg.sales_channel == "WDN":
            return f"AND {channel_column} = 'WALTON DISTRIBUTOR'"
        if cfg.sales_channel == "MDN":
            return f"AND {channel_column} = 'MARCEL DISTRIBUTOR'"
        if cfg.sales_channel == "Single Party" and cfg.single_party_id:
            return f"AND {party_column} = {int(cfg.single_party_id)}"
        return ""

    def fetch_party_receivable(self,cfg):
        self.progress("Fetching Party Receivable")
        try:
            with self.db.connect_trino() as con:
                party_filter = self._single_party_filter(cfg, "party_id")
                return pd.read_sql(self._q(PARTY_RECEIVABLE_TRINO,calc_end=cfg.stock_start.replace(day=__import__('calendar').monthrange(cfg.stock_year,cfg.stock_month)[1]).isoformat(),party_filter=party_filter),con)
        except Exception:
            self.progress("Trino receivable failed; trying Oracle")
            con=self.db.connect_oracle()
            try:
                party_filter = self._single_party_filter(cfg, "PARTY_ID")
                return pd.read_sql(PARTY_RECEIVABLE_ORACLE.format(calc_end_oracle=oracle_date(cfg.stock_start.replace(day=__import__('calendar').monthrange(cfg.stock_year,cfg.stock_month)[1])),party_filter=party_filter),con)
            finally:
                con.close()

    @staticmethod
    def _single_party_filter(cfg, party_column):
        if cfg.sales_channel == "Single Party" and cfg.single_party_id:
            return f"AND {party_column} = {int(cfg.single_party_id)}"
        return ""

    def fetch_party_info(self):
        self.progress("Fetching Party Information")
        with self.db.connect_trino() as con:
            return pd.read_sql(PARTY_INFO,con)

    def fetch_party_info_filtered(self, cfg):
        self.progress("Fetching Party Information for selected filter")
        party_filter = self._party_filter(cfg, "CUST_ACCT.SALES_CHANNEL_CODE", "PARTY.PARTY_ID")
        query = self._q(PARTY_INFO_FILTERED, party_filter=party_filter)
        with self.db.connect_trino() as con:
            return pd.read_sql(query, con)

    def fetch_current_receiving(self,cfg):
        self.progress("Fetching current-month receiving")
        with self.db.connect_trino() as con:
            return pd.read_sql(self._q(CURRENT_RECEIVING,start=cfg.stock_start.isoformat(),end=cfg.next_month_start.isoformat()),con)

    def fetch_previous_stock(self,cfg):
        from app.utils.dates import previous_month_end
        self.progress("Fetching previous-month user stock")
        prev=previous_month_end(cfg.stock_year,cfg.stock_month)
        with self.db.connect_trino() as con:
            return pd.read_sql(self._q(PREVIOUS_STOCK,prev_end=prev.isoformat()),con)

    @staticmethod
    def load_group_map(path):
        try:
            d=pd.read_csv(path)
            return dict(zip(d["Party_ID"],d["Group_id"]))
        except Exception:
            return {}

