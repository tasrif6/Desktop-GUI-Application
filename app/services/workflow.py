from dataclasses import asdict
from pathlib import Path
import pandas as pd
from app.repositories.db import DatabaseManager
from app.services.data_service import DataService
from app.business.processing import *
from app.business.exclusion_engine import ExclusionEngine
from app.business.rebate_engine import RebateEngine
from app.config import settings
from app.utils.dates import month_label

class Workflow:
    def __init__(self, config, progress=None):
        self.config=config
        self.progress=progress or (lambda msg:None)
        self.db=DatabaseManager()
        self.data={}
        self.group_map = config.group_map if getattr(config, "group_map", None) else DataService.load_group_map(settings.GROUP_FILE)
        
    def run(self):
        try:
            for step in range(1, 8):
                self.run_step(step)
            return self.data
        finally:
            self.db.close()

    def run_step(self, step):
        ds = DataService(self.db, self.progress)
        if step == 1:
            self.progress("Loading configured party group mapping")
            stock = normalize_ids(ds.fetch_entered_stock(self.config))
            self.data["entered_stock_raw"] = stock.copy()
            if self.config.excluded_party_ids:
                stock = stock[~stock["PARTY_ID"].isin(self.config.excluded_party_ids)].copy()
            if self.config.use_exclusive_selection:
                stock = stock[stock["PARTY_ID"].isin(self.config.exclusive_party_ids)].copy()
            self.data["entered_stock"] = stock.copy()
            stock_group = apply_group_mapping(stock, self.group_map) if self.config.use_group_mapping else stock.copy()
            self._stock2_all = summarize_stock(stock_group)
            self.data["entered_stock_summary"] = self._stock2_all.copy()
            return self.data

        if step == 2:
            party_info = normalize_ids(ds.fetch_party_info_filtered(self.config))
            selected_group_ids = set(self.config.exclusive_party_ids)
            if self.config.use_group_mapping:
                selected_group_ids = {self.group_map.get(pid, pid) for pid in self.config.exclusive_party_ids}
            self._exclusive_excluded = pd.DataFrame()
            if self.config.use_exclusive_selection:
                nonselected = self._stock2_all[~self._stock2_all["PARTY_ID"].isin(selected_group_ids)].copy()
                if not nonselected.empty:
                    nonselected = nonselected.groupby("PARTY_ID", as_index=False)["Qty"].sum()
                    self._exclusive_excluded = nonselected.merge(
                        party_info[["PARTY_ID", "party_name", "sales_channel_code", "customer_id"]],
                        on="PARTY_ID", how="left")
                    self._exclusive_excluded["excluded"] = True
                    self._exclusive_excluded["exclusion_reason"] = "Not in selected exclusive party list"
            self._stock2 = self._stock2_all.copy()
            if self.config.use_exclusive_selection:
                self._stock2 = self._stock2[self._stock2["PARTY_ID"].isin(selected_group_ids)].copy()
            self._party_info = party_info
            self.data["party_info"] = party_info.copy()
            self.data["party_duplicates"] = duplicate_check(party_info)
            return self.data

        if step == 3:
            print("[PartyLifting] WORKFLOW step 3 START", flush=True)
            print("[PartyLifting] normalize IDs START", flush=True)
            lifting = normalize_ids(ds.fetch_party_lifting(self.config))
            print(f"[PartyLifting] normalize IDs DONE; rows={len(lifting):,}, shape={lifting.shape}", flush=True)
            print("[PartyLifting] raw-data copy START", flush=True)
            self.data["party_lefting_raw"] = lifting.copy()
            print("[PartyLifting] raw-data copy DONE", flush=True)
            lifting2 = summarize_lifting(lifting, self.group_map if self.config.use_group_mapping else {})
            print("[PartyLifting] summarized-data assignment START", flush=True)
            self.data["party_lefting"] = lifting2.copy()
            print("[PartyLifting] summarized-data assignment DONE", flush=True)
            main = build_main_df(self._stock2, lifting2)
            print("[PartyLifting] effective-stock detail copy START", flush=True)
            self.data["effective_stock_detail"] = main.copy()
            print("[PartyLifting] effective-stock detail copy DONE", flush=True)
            self._grouped = aggregate_party(main)
            print(f"[PartyLifting] WORKFLOW step 3 DONE grouped_parties={len(self._grouped):,}", flush=True)
            return self.data

        if step == 4:
            receivable = normalize_ids(ds.fetch_party_receivable(self.config))
            self.data["party_receivable_raw"] = receivable.copy()
            grouped = merge_receivable(self._grouped, receivable, self.group_map if self.config.use_group_mapping else {})
            grouped = party_percent(grouped)
            self._grouped = merge_party_info(grouped, self._party_info)
            return self.data

        if step == 5:
            current = normalize_ids(ds.fetch_current_receiving(self.config))
            prev = normalize_ids(ds.fetch_previous_stock(self.config))
            group_map = self.group_map if self.config.use_group_mapping else {}
            current = apply_group_mapping(current, group_map)
            prev = apply_group_mapping(prev, group_map)
            current = current.groupby("PARTY_ID", as_index=False)[["CURR_RCV_QTY", "CURR_RCV_VAL"]].sum() if not current.empty else pd.DataFrame(columns=["PARTY_ID", "CURR_RCV_QTY", "CURR_RCV_VAL"])
            prev = prev.groupby("PARTY_ID", as_index=False)[["PREV_USER_STOCK_VALUE", "PREV_USER_STOCK_VALUE_2PER"]].sum() if not prev.empty else pd.DataFrame(columns=["PARTY_ID", "PREV_USER_STOCK_VALUE", "PREV_USER_STOCK_VALUE_2PER"])
            self.data["current_receiving"] = current.copy()
            self.data["previous_stock"] = prev.copy()
            self._grouped = self._grouped.merge(current, on="PARTY_ID", how="left").merge(prev, on="PARTY_ID", how="left").fillna(0)
            self.data["party_calculation_base"] = self._grouped.copy()
            self.data["grouped_parties"] = self._grouped.copy()
            return self.data

        if step == 6:
            self.progress("Evaluating exclusion conditions")
            lifting_party_ids = self.data["party_lefting"].get("PARTY_ID", pd.Series(dtype="Int64"))
            eligible, excluded = ExclusionEngine(self.config.exclusion).evaluate(
                self._grouped,
                lifting_party_ids,
            )
            if not self._exclusive_excluded.empty:
                excluded = pd.concat([excluded, self._exclusive_excluded], ignore_index=True, sort=False)
            self.data["excluded_parties"] = excluded.copy()
            self.data["eligible_before_rebate"] = eligible.copy()
            self._eligible = eligible
            return self.data

        if step == 7:
            self.progress("Calculating rebate for eligible parties")
            self.data["rebate_results"] = RebateEngine(self.config.rebate_rules).calculate(self._eligible)
            return self.data

        # if step == 8:
        #     self.progress("Final validation and high-stock classification")
        #     hs = self._grouped.copy()
        #     high_stock_condition = ((hs["CURR_RCV_QTY"] == 0) & (hs["PREV_USER_STOCK_VALUE"] != 0) & (hs["EffectiveStockValue"] > hs["PREV_USER_STOCK_VALUE"] * self.config.exclusion.high_stock_multiplier))
        #     self.data["high_stock"] = hs.loc[~high_stock_condition].copy()
        #     self.data["final_results"] = self.data["rebate_results"].copy()
        #     self.progress(f"Completed: {len(self.data['final_results']):,} eligible parties, {len(self.data.get('excluded_parties', [])): ,} excluded parties")
        #     # Step-by-step ("Next Step") runs never go through run()'s
        #     # finally block, so the DB engine/connections would otherwise
        #     # stay open indefinitely once the last step finishes. Close
        #     # them here too; close() is idempotent (safe to call twice).
        #     self.db.close()
        #     return self.data

        raise ValueError(f"Unknown workflow step: {step}")
