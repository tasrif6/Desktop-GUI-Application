import pandas as pd
from datetime import datetime
import time

class ExclusionEngine:
    def __init__(self,rules):
        self.rules=rules

    def evaluate(self, df, lifting_party_ids):
        print(f"[PartyLifting] exclusion evaluation START parties={len(df):,}", flush=True)
        x=df.copy()
        if x.empty:
            return x, x.copy()
        reasons={i:[] for i in x.index}
        if "HasMatchingModel" in x:
            missing_lifting = ~x["HasMatchingModel"].fillna(False).astype(bool)
            for i in x.index[missing_lifting]:
                reasons[i].append("No matching model found in Party Lifting")
        elif "Ship_Qty" in x:
            missing_lifting = x["Ship_Qty"].eq(0)
            for i in x.index[missing_lifting]:
                reasons[i].append("No Party Lifting record found")
                
        if "PARTY_ID" in x:
            stage_start = time.perf_counter()
            print("[PartyLifting] PARTY_ID membership exclusion START", flush=True)
            lifting_party_ids = pd.Index(lifting_party_ids).dropna().unique()
            missing_lifting = ~x["PARTY_ID"].isin(lifting_party_ids)
            print(f"[PartyLifting] PARTY_ID membership exclusion DONE in {time.perf_counter() - stage_start:.2f}s; lifting_ids={len(lifting_party_ids):,}, missing={int(missing_lifting.sum()):,}", flush=True)
            for i in x.index[missing_lifting]:
                reasons[i].append("No Party Lifting record found")

        # Preserve the notebook's global switch: if any Balance < threshold,
        # lower Walton/Marcel minimum-stock thresholds are used for the run.
        negative_mode = self.rules.negative_balance_mode and (x["Balance"] < self.rules.negative_balance_threshold).any()

        w_thr=self.rules.walton_stock_threshold_negative if negative_mode else self.rules.walton_stock_threshold_normal
        m_thr=self.rules.marcel_stock_threshold_negative if negative_mode else self.rules.marcel_stock_threshold_normal

        w=(x["sales_channel_code"].eq("WALTON DISTRIBUTOR")) & (x["EffectiveStockValue"]<w_thr)
        m=(x["sales_channel_code"].eq("MARCEL DISTRIBUTOR")) & (x["EffectiveStockValue"]<m_thr)

        w_reason=f"Stock < {w_thr:,.0f} (Walton; {'negative-balance mode' if negative_mode else 'normal mode'})"
        m_reason=f"Stock < {m_thr:,.0f} (Marcel; {'negative-balance mode' if negative_mode else 'normal mode'})"
        for i in x.index[w]: reasons[i].append(w_reason)
        for i in x.index[m]: reasons[i].append(m_reason)

        if self.rules.apply_high_stock_rule and "CURR_RCV_QTY" in x and "PREV_USER_STOCK_VALUE" in x:
            high=((x["CURR_RCV_QTY"]==0)&(x["PREV_USER_STOCK_VALUE"]!=0)&
                  (x["EffectiveStockValue"]>x["PREV_USER_STOCK_VALUE"]*self.rules.high_stock_multiplier))
            for i in x.index[high]:
                reasons[i].append("High Stock without receiving new stock")

        x["exclusion_reason"]=[ "; ".join(reasons[i]) for i in x.index]
        x["excluded"]=x["exclusion_reason"].ne("")
        x["exclusion_evaluated_at"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        excluded=x.loc[x["excluded"]].copy()
        eligible=x.loc[~x["excluded"]].copy()
        print(f"[PartyLifting] exclusion evaluation DONE eligible={len(eligible):,}, excluded={len(excluded):,}", flush=True)
        return eligible,excluded
