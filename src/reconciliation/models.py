"""
reconciliation/models.py
------------------------
Structured data models for cross-table reconciliation audits.
Conforms to Phase 5 specification for DATA-OBSERVED cross-table audits.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any


class ReconciliationStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    UNRESOLVED = "UNRESOLVED"
    FAIL = "FAIL"


class ReconciliationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ReconciliationResult:
    """Represents the execution outcome of an advisory cross-table reconciliation audit."""
    run_id: str
    rule_code: str
    source_tables: str
    dimension: str
    entity: str
    expected_value: Optional[float]
    observed_value: Optional[float]
    absolute_difference: Optional[float]
    relative_difference: Optional[float]
    absolute_tolerance: float
    relative_tolerance: float
    status: str
    severity: str
    message: str
    rule_category: str = "DATA-OBSERVED"
    reconciliation_id: Optional[int] = None
    executed_at: Optional[str] = None

    def __post_init__(self):
        if not self.executed_at:
            self.executed_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
