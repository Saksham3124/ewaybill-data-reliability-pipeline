"""
statistics/models.py
--------------------
Structured data models for Year-over-Year Statistical Analysis.
Enforces explicit distinction between statistical significance and data-quality failure.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any


class StatisticalStatus(str, Enum):
    NO_MATERIAL_STATISTICAL_CHANGE = "NO_MATERIAL_STATISTICAL_CHANGE"
    STATISTICALLY_DIFFERENT = "STATISTICALLY_DIFFERENT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class StatisticalResult:
    """Represents the outcome of a Year-over-Year statistical test or metric comparison."""
    run_id: str
    dimension: str
    metric: str
    test_method: str
    status: str
    interpretation: str
    comparison_year: str = "2023-24"
    reference_year: str = "2022-23"
    sample_size_reference: Optional[int] = None
    sample_size_comparison: Optional[int] = None
    statistic: Optional[float] = None
    p_value: Optional[float] = None
    alpha: Optional[float] = None
    psi_value: Optional[float] = None
    psi_threshold: Optional[float] = None
    statistical_id: Optional[int] = None
    executed_at: Optional[str] = None

    def __post_init__(self):
        if not self.executed_at:
            self.executed_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
