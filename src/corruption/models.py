"""
src/corruption/models.py
------------------------
Structured data models for Phase 7 Controlled Corruption Simulation and Detection Testing.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any


class CorruptionType(str, Enum):
    MISSING_RECORD = "MISSING_RECORD"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    INVALID_DOMAIN = "INVALID_DOMAIN"
    ALTERED_NUMERIC = "ALTERED_NUMERIC"
    MISSING_ENTITY_COLUMN = "MISSING_ENTITY_COLUMN"
    NUMERIC_TO_TEXT = "NUMERIC_TO_TEXT"
    DISTRIBUTION_SHIFT = "DISTRIBUTION_SHIFT"


@dataclass
class CorruptionScenario:
    """Defines a deterministic controlled corruption scenario."""
    scenario_id: str
    corruption_type: str
    expected_detector: str
    description: str
    source_year: str = "2023-24"
    source_table: str = ""
    target_field: str = ""
    target_record: str = ""
    original_value: Any = None
    corrupted_value: Any = None
    random_seed: Optional[int] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DetectionResult:
    """Structured outcome of running detection pipelines on a corrupted dataset."""
    scenario_id: str
    corruption_type: str
    expected_detector: str
    actual_detector: Optional[str]
    detected: bool
    pipeline_blocked: bool
    false_positive: bool
    affected_table: str
    affected_field: str
    affected_record: str
    original_value: Any
    corrupted_value: Any
    detection_message: str
    execution_timestamp: Optional[str] = None
    evidence_details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.execution_timestamp:
            self.execution_timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
