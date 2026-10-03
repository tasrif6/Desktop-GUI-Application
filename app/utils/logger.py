import logging
from pathlib import Path

def setup_logger():
    logger=logging.getLogger("stock_rebate")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        h=logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(h)
    return logger
