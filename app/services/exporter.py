from pathlib import Path
import pandas as pd
from app.config.settings import OUTPUT_DIR

def _month_output_dir(year, month_label_text):
    path = OUTPUT_DIR / str(year) / month_label_text
    path.mkdir(parents=True, exist_ok=True)
    return path

def export_dataframe(df, year, month_label_text, filename):
    out_dir = _month_output_dir(year, month_label_text)
    path = out_dir / filename
    df.to_csv(path, index=False)
    return path

def export_excluded(df, year, month_label_text):
    return export_dataframe(df, year, month_label_text, f"Excluded_Parties_{month_label_text}.csv")

def export_results(data, year, month_label_text):
    out_dir = _month_output_dir(year, month_label_text)
    exported = []
    for key, sheet in [
        ("excluded_parties", "ExcludedParties"),
        ("rebate_results", "RebateResults"),
        ("high_stock", "HighStock"),
        ("final_results", "FinalResults"),
    ]:
        df = data.get(key)
        if df is not None and isinstance(df, pd.DataFrame):
            path = out_dir / f"{month_label_text}_{sheet}.csv"
            df.to_csv(path, index=False)
            exported.append(path)
    return exported