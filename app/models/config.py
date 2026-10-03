from dataclasses import dataclass, field
from datetime import date
from typing import Optional

@dataclass
class ExclusionRules:
    negative_balance_threshold: float = 50000.0
    negative_balance_mode: bool = True
    walton_stock_threshold_normal: float = 400000.0
    marcel_stock_threshold_normal: float = 200000.0
    walton_stock_threshold_negative: float = 100000.0
    marcel_stock_threshold_negative: float = 100000.0
    high_stock_multiplier: float = 1.20
    apply_high_stock_rule: bool = True

@dataclass
class RebateRule:
    min_percent: Optional[float]
    max_percent: Optional[float]
    rebate: float

@dataclass
class CalculationConfig:
    stock_month: int
    stock_year: int
    sales_channel: str = "All"
    exclusive_party_ids: list[int] = field(default_factory=list)
    excluded_party_ids: list[int] = field(default_factory=list)
    use_exclusive_selection: bool = False
    use_group_mapping: bool = True
    exclusion: ExclusionRules = field(default_factory=ExclusionRules)
    rebate_rules: list[RebateRule] = field(default_factory=list)
    single_party_id: Optional[int] = None
    group_map: Optional[dict] = None

    @property
    def stock_start(self) -> date:
        return date(self.stock_year, self.stock_month, 1)

    @property
    def next_month_start(self) -> date:
        if self.stock_month == 12:
            return date(self.stock_year + 1, 1, 1)
        return date(self.stock_year, self.stock_month + 1, 1)

    @property
    def stock_entry_start(self) -> date:
        return date(self.stock_year, self.stock_month, 24)
