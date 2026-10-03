import pandas as pd
import numpy as np
import time

def normalize_ids(df):
    if df is None or df.empty or "PARTY_ID" not in df.columns: return df
    df=df.copy()
    df["PARTY_ID"]=pd.to_numeric(df["PARTY_ID"],errors="coerce").astype("Int64")
    return df

# def apply_static_exclusions(stock, excluded):
#     if stock.empty or excluded.empty or "PARTY_ID" not in excluded: return stock.copy()
#     return stock.loc[~stock["PARTY_ID"].isin(excluded["PARTY_ID"])].copy()

def apply_group_mapping(df, group_map):
    if df.empty or not group_map: return df.copy()
    x=df.copy()
    x["PARTY_ID"]=x["PARTY_ID"].map(group_map).fillna(x["PARTY_ID"])
    return x

def summarize_stock(stock):
    if stock.empty: return stock.copy()
    return stock.groupby(["PARTY_ID", "item_code", "model"],as_index=False, dropna = False)["Qty"].sum()

def summarize_lifting(lifting, group_map):
    print(f"[PartyLifting] summarize_lifting START rows={len(lifting):,}, group_map={len(group_map):,}", flush=True)
    stage_start = time.perf_counter()
    print("[PartyLifting] group mapping START", flush=True)
    x=apply_group_mapping(lifting,group_map)
    print(f"[PartyLifting] group mapping DONE in {time.perf_counter() - stage_start:.2f}s; rows={len(x):,}", flush=True)
    if x.empty:
        print("[PartyLifting] summarize_lifting DONE; empty input", flush=True)
        return x
    stage_start = time.perf_counter()
    print("[PartyLifting] lifting groupby PARTY_ID/item_code/model START", flush=True)
    x=x.groupby(["PARTY_ID","item_code", "model"],as_index=False, dropna = False)[["Ship_Qty","Amount"]].sum()
    print(f"[PartyLifting] lifting groupby DONE in {time.perf_counter() - stage_start:.2f}s; rows={len(x):,}", flush=True)
    stage_start = time.perf_counter()
    print("[PartyLifting] average-rate calculation START", flush=True)
    x["avg_rate"]=np.where(x["Ship_Qty"]!=0,x["Amount"]/x["Ship_Qty"],0)
    print(f"[PartyLifting] average-rate calculation DONE in {time.perf_counter() - stage_start:.2f}s", flush=True)
    print(f"[PartyLifting] summarize_lifting DONE output_rows={len(x):,}", flush=True)
    return x

def build_main_df(stock2,lifting2):
    print(f"[PartyLifting] stock/lifting merge START stock_rows={len(stock2):,}, lifting_rows={len(lifting2):,}", flush=True)
    stage_start = time.perf_counter()
    x=pd.merge(
        stock2,
        lifting2,
        how="outer",
        on=["PARTY_ID", "item_code", "model"],
        indicator="_stock_lifting_match",
    )
    print(f"[PartyLifting] stock/lifting merge DONE in {time.perf_counter() - stage_start:.2f}s; output_rows={len(x):,}", flush=True)
    stage_start = time.perf_counter()
    print("[PartyLifting] effective-stock calculations START", flush=True)

    x["HasMatchingModel"] = x["_stock_lifting_match"].eq("both")

    for column in ("Qty", "Ship_Qty", "Amount", "avg_rate"):
        if column not in x:
            x[column] = 0
    x[["Qty", "Ship_Qty", "Amount", "avg_rate"]] = x[["Qty", "Ship_Qty", "Amount", "avg_rate"]].fillna(0)
    x["EffectiveStock"]=np.minimum(x["Qty"],x["Ship_Qty"])
    x["EffectiveStockValue"]=x["EffectiveStock"]*x["avg_rate"]
    print(f"[PartyLifting] effective-stock calculations DONE in {time.perf_counter() - stage_start:.2f}s", flush=True)
    return x

def aggregate_party(main):
    print(f"[PartyLifting] aggregate_party START rows={len(main):,}", flush=True)
    stage_start = time.perf_counter()
    if main.empty:
        result = pd.DataFrame(columns=["PARTY_ID", "EffectiveStockValue", "EffectiveStock", "Ship_Qty", "HasMatchingModel"])
        print("[PartyLifting] aggregate_party DONE; empty input", flush=True)
        return result
    result = main.groupby("PARTY_ID",as_index=False).agg(
        EffectiveStockValue=("EffectiveStockValue","sum"),
        EffectiveStock=("EffectiveStock","sum"),
        Ship_Qty=("Ship_Qty","sum"),
        HasMatchingModel=("HasMatchingModel", "any"),
    )
    print(f"[PartyLifting] aggregate_party DONE in {time.perf_counter() - stage_start:.2f}s; parties={len(result):,}", flush=True)
    return result

def merge_receivable(grouped, receivable, group_map):
    if "PARTY_ID" not in grouped:
        grouped = pd.DataFrame(columns=["PARTY_ID", "EffectiveStockValue", "EffectiveStock", "Ship_Qty"])
    r=apply_group_mapping(receivable,group_map)
    if r.empty or "PARTY_ID" not in r or "Balance" not in r:
        r=pd.DataFrame(columns=["PARTY_ID", "Balance"])
    else:
        r=r.groupby("PARTY_ID",as_index=False)["Balance"].sum()
    return pd.merge(grouped,r,on="PARTY_ID",how="left").fillna({"Balance": 0})

def party_percent(df):
    x=df.copy()
    if x.empty:
        x["PercentOnReceivable"] = pd.Series(dtype=float)
        return x
    balance = pd.to_numeric(x["Balance"], errors="coerce").fillna(0).to_numpy(dtype=float)
    stock_value = pd.to_numeric(x["EffectiveStockValue"], errors="coerce").fillna(0).to_numpy(dtype=float)
    percent = np.divide(
        stock_value * 100,
        balance,
        out=np.zeros_like(stock_value, dtype=float),
        where=balance != 0,
    )
    percent[(balance == 0) & (stock_value > 0)] = np.inf
    x["PercentOnReceivable"] = percent
    return x

def duplicate_check(party_info):
    if party_info.empty: return pd.DataFrame()
    return party_info.loc[party_info["PARTY_ID"].duplicated(keep=False)].copy()

def merge_party_info(df, party_info):
    return pd.merge(df, party_info, on="PARTY_ID", how="left")
