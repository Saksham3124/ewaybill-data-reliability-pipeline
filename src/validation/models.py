"""
validation/models.py
--------------------
Data structures and enums for validation results.
Adheres to Phase 4 specification:
- Common result structure
- Statuses: PASS, WARNING, FAIL
- Severity levels: INFO, WARNING, ERROR, CRITICAL
- Structured metrics and timestamps
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Dict


class ValidationStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class ValidationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ValidationCategory(str, Enum):
    SCHEMA = "SCHEMA"
    COMPLETENESS = "COMPLETENESS"
    UNIQUENESS = "UNIQUENESS"
    DOMAIN = "DOMAIN"
    NUMERIC = "NUMERIC"
    STRUCTURAL = "STRUCTURAL"
    SOURCE_TOTAL = "SOURCE_TOTAL"


@dataclass
class ValidationCheckResult:
    """Standardized result for every validation rule execution."""
    check_id: str
    check_category: str  # ValidationCategory value or str
    check_name: str
    table_name: str
    status: str          # "PASS", "WARNING", "FAIL"
    severity: str        # "INFO", "WARNING", "ERROR", "CRITICAL"
    expected: Any
    observed: Any
    difference: Optional[float]
    affected_records: int
    message: str
    execution_timestamp: str
    run_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts result to dictionary."""
        return asdict(self)
