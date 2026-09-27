"""
src/incidents/models.py
-----------------------
Structured data models for pipeline incidents.

Adheres strictly to the project's governance boundaries:
- Captures blocking data-integrity failures with exact check metadata.
- Distinguishes CRITICAL, ERROR, and WARNING severities.
- Preserves full underlying failure records for aggregated auditability.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List


class IncidentSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


@dataclass
class Incident:
    """
    Represents a blocking data integrity or validation failure incident halting trusted loading.
    
    Contains all minimum governance fields:
    - incident_id: Unique database primary key
    - run_id: Pipeline execution identifier
    - severity: CRITICAL, ERROR, or WARNING
    - status: OPEN, ACKNOWLEDGED, or RESOLVED
    - failure_type: Classification (e.g. DATA_INTEGRITY_FAILURE, SCHEMA_VALIDATION_FAILURE)
    - source_table: Primary table affected
    - check_id: Primary check or rule identifier (e.g. SCH-02, CMP-01)
    - check_name: Descriptive name of the failing check
    - expected_value: Benchmark/expected value (NULL where not provided)
    - observed_value: Actual observed value (NULL where not provided)
    - difference: Numeric difference where applicable (NULL where not applicable)
    - affected_record_count: Number of records affected where applicable
    - detection_timestamp: Timestamp when failure was detected
    - resolution_timestamp: Timestamp when resolved (NULL while OPEN)
    - resolution_notes: Notes on resolution (NULL while OPEN)
    - triggering_failures: Full structured array of all underlying failure items
    - alert_sent: Whether notification has been dispatched
    - alert_sent_at: Timestamp of notification dispatch
    """
    run_id: str
    severity: str
    failure_type: str = "DATA_INTEGRITY_FAILURE"
    incident_id: Optional[int] = None
    status: str = IncidentStatus.OPEN.value
    source_table: Optional[str] = None
    check_id: Optional[str] = None
    check_name: Optional[str] = None
    expected_value: Optional[str] = None
    observed_value: Optional[str] = None
    difference: Optional[float] = None
    affected_record_count: int = 0
    title: str = ""
    description: str = ""
    triggering_failures: List[Dict[str, Any]] = field(default_factory=list)
    detection_timestamp: Optional[str] = None
    resolution_timestamp: Optional[str] = None
    resolution_notes: Optional[str] = None
    alert_sent: bool = False
    alert_sent_at: Optional[str] = None
    # Backward compatibility aliases
    incident_type: Optional[str] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None

    def __post_init__(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        if not self.detection_timestamp:
            self.detection_timestamp = self.created_at or now_iso
        if not self.created_at:
            self.created_at = self.detection_timestamp
        if not self.incident_type:
            self.incident_type = self.failure_type
        if not self.resolved_at and self.resolution_timestamp:
            self.resolved_at = self.resolution_timestamp
        elif not self.resolution_timestamp and self.resolved_at:
            self.resolution_timestamp = self.resolved_at

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
