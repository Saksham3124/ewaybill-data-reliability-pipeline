"""
src/incidents
-------------
Incident management module for data reliability failures.
"""

from src.incidents.models import Incident, IncidentSeverity, IncidentStatus
from src.incidents.manager import IncidentManager

__all__ = [
    "Incident",
    "IncidentSeverity",
    "IncidentStatus",
    "IncidentManager",
]
