import pandas as pd
import math

class RebateEngine:
    """Rebate engine only. Eligibility/exclusion is handled elsewhere."""
    def __init__(self,rules): self.rules=rules

    def get_rebate(self, percent):
        if percent is None or (isinstance(percent,float) and math.isnan(percent)):
            return 0.0
        for r in self.rules:
            lo=r.min_percent
            hi=r.max_percent
            if lo is None and hi is not None and percent < hi: return r.rebate
            if lo is not None and hi is None and percent >= lo: return r.rebate
            if lo is not None and hi is not None and lo <= percent < hi: return r.rebate
        return 0.0

    def calculate(self, eligible):
        x=eligible.copy()
        if x.empty:
            x["Rebate2"]=pd.Series(dtype=float); x["Rebate1"]=0.0; x["TotalRebate"]=0.0
            return x
        x["Rebate1"]=0.0
        x["Rebate2"]=x["PercentOnReceivable"].apply(self.get_rebate)
        x["TotalRebate"]=x["Rebate1"]+x["Rebate2"]
        return x
