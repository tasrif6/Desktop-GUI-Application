from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(ROOT / "output")))
GROUP_FILE = ROOT / "EXCLUDE_&_GROUP_PARTY" / "GROUP" / "GROUP_PARTY.csv"

TRINO_URL = os.getenv("TRINO_URL", "")
ORACLE_DSN = os.getenv("ORACLE_DSN", "")
ORACLE_CLIENT_LIB = os.getenv("ORACLE_CLIENT_LIB", "")

EXCLUDED_ITEM_CODES = [228258]
EXCLUDED_PRODUCTS = ["AIRCONDITIONER-OUTDOOR"]

DEFAULT_EXCLUSION_RULES = {
    "negative_balance_threshold": 50000.0,
    "negative_balance_mode": True,
    "walton_stock_threshold_normal": 400000.0,
    "marcel_stock_threshold_normal": 200000.0,
    "walton_stock_threshold_negative": 100000.0,
    "marcel_stock_threshold_negative": 100000.0,
    "high_stock_multiplier": 1.20,
    "apply_high_stock_rule": True,
}

DEFAULT_REBATE_RULES = [
    {"min_percent": 100.0, "max_percent": None, "rebate": 0.25},
    {"min_percent": 90.0, "max_percent": 100.0, "rebate": 0.23},
    {"min_percent": 80.0, "max_percent": 90.0, "rebate": 0.21},
    {"min_percent": 70.0, "max_percent": 80.0, "rebate": 0.19},
    {"min_percent": 60.0, "max_percent": 70.0, "rebate": 0.17},
    {"min_percent": 50.0, "max_percent": 60.0, "rebate": 0.15},
    {"min_percent": 40.0, "max_percent": 50.0, "rebate": 0.13},
    {"min_percent": 30.0, "max_percent": 40.0, "rebate": 0.11},
    {"min_percent": 0.0, "max_percent": 30.0, "rebate": 0.09},
    {"min_percent": None, "max_percent": 0.0, "rebate": 0.25},
]
