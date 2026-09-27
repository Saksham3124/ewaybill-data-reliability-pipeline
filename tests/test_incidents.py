"""
tests/test_incidents.py
-----------------------
Unit and integration tests for Phase 9 incident management.

Verifies:
1. Incident creation and schema adherence (all 14 minimum required fields).
2. NULL preservation for non-existent check attributes.
3. Strict severity preservation (CRITICAL > ERROR > WARNING).
4. Run ID lineage preservation.
5. Deterministic and idempotent incident recording (no duplicates on retry).
6. Multi-failure aggregation policy.
7. Strict exclusion of advisory findings (OTHER TERRITORY UNRESOLVED, STATISTICALLY_DIFFERENT)
   from blocking incident creation.
8. Audit markdown file generation.
"""

import os
import uuid
import pytest
from datetime import datetime, timezone

from src.database.connection import DatabaseManager
from src.incidents.models import Incident, IncidentSeverity, IncidentStatus
from src.incidents.manager import IncidentManager


def get_test_db():
    return DatabaseManager(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        dbname=os.getenv("POSTGRES_DB", "ewaybill_dw"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "Saksham@3124")
    )


# -----------------------------------------------------------------------------
# 1. Incident Creation & Minimum Fields
# -----------------------------------------------------------------------------

def test_incident_creation_and_required_fields():
    """Verifies that an Incident contains all 14 minimum required governance fields."""
    run_id = str(uuid.uuid4())
    failure = {
        "check_id": "NUM-01",
        "check_name": "Non-negative movement values",
        "table_name": "table_iv_inward",
        "status": "FAIL",
        "severity": "CRITICAL",
        "expected_value": ">= 0",
        "observed_value": "-150.25",
        "difference": 150.25,
        "affected_records": 3,
        "message": "Found 3 negative values in inward movements."
    }

    mgr = IncidentManager()
    incident = mgr.create_incident(run_id=run_id, failures=[failure])

    # Minimum required fields
    assert incident.run_id == run_id
    assert incident.severity == IncidentSeverity.CRITICAL.value
    assert incident.status == IncidentStatus.OPEN.value
    assert incident.failure_type == "DATA_INTEGRITY_FAILURE"
    assert incident.source_table == "table_iv_inward"
    assert incident.check_id == "NUM-01"
    assert incident.check_name == "Non-negative movement values"
    assert incident.expected_value == ">= 0"
    assert incident.observed_value == "-150.25"
    assert incident.difference == 150.25
    assert incident.affected_record_count == 3
    assert incident.detection_timestamp is not None
    assert incident.resolution_timestamp is None
    assert incident.resolution_notes is None
    assert len(incident.triggering_failures) == 1


def test_incident_null_preservation():
    """Verifies that missing check attributes remain NULL without invented values."""
    run_id = str(uuid.uuid4())
    failure = {
        "check_id": "SCH-02",
        "check_name": "Expected columns presence",
        "table_name": "table_i_interstate",
        "status": "FAIL",
        "severity": "CRITICAL",
        "expected_value": None,
        "observed_value": None,
        "difference": None,
        "affected_records": 0,
        "message": "Missing required column 'state'."
    }

    mgr = IncidentManager()
    incident = mgr.create_incident(run_id=run_id, failures=[failure])

    assert incident.expected_value is None
    assert incident.observed_value is None
    assert incident.difference is None
    assert incident.affected_record_count == 0


# -----------------------------------------------------------------------------
# 2. Severity Hierarchy Preservation
# -----------------------------------------------------------------------------

def test_severity_preservation():
    """Verifies that the highest severity among failures determines incident severity."""
    mgr = IncidentManager()
    run_id = str(uuid.uuid4())

    # Single CRITICAL
    inc_crit = mgr.create_incident(run_id, [{"check_id": "C1", "severity": "CRITICAL", "status": "FAIL"}])
    assert inc_crit.severity == IncidentSeverity.CRITICAL.value

    # Single ERROR
    inc_err = mgr.create_incident(run_id, [{"check_id": "E1", "severity": "ERROR", "status": "FAIL"}])
    assert inc_err.severity == IncidentSeverity.ERROR.value

    # Single WARNING
    inc_warn = mgr.create_incident(run_id, [{"check_id": "W1", "severity": "WARNING", "status": "FAIL"}])
    assert inc_warn.severity == IncidentSeverity.WARNING.value

    # Mixed: CRITICAL + ERROR -> CRITICAL
    inc_mixed = mgr.create_incident(run_id, [
        {"check_id": "E1", "severity": "ERROR", "status": "FAIL"},
        {"check_id": "C1", "severity": "CRITICAL", "status": "FAIL"}
    ])
    assert inc_mixed.severity == IncidentSeverity.CRITICAL.value
    # Primary check ID should be the CRITICAL one
    assert inc_mixed.check_id == "C1"


# -----------------------------------------------------------------------------
# 3. Aggregation of Multiple Failures
# -----------------------------------------------------------------------------

def test_multiple_failures_aggregated_correctly():
    """Verifies that multiple failures in a single run are aggregated cleanly."""
    run_id = str(uuid.uuid4())
    failures = [
        {
            "check_id": "UNQ-01",
            "check_name": "Unique composite key",
            "table_name": "table_ii_state",
            "severity": "CRITICAL",
            "status": "FAIL",
            "affected_records": 2
        },
        {
            "check_id": "NUM-02",
            "check_name": "Numeric type check",
            "table_name": "table_iv_inward",
            "severity": "ERROR",
            "status": "FAIL",
            "affected_records": 5
        }
    ]

    mgr = IncidentManager()
    incident = mgr.create_incident(run_id=run_id, failures=failures)

    assert incident.severity == IncidentSeverity.CRITICAL.value
    assert incident.check_id == "UNQ-01"
    assert incident.affected_record_count == 7
    assert len(incident.triggering_failures) == 2
    assert "table_ii_state" in incident.description


# -----------------------------------------------------------------------------
# 4. Lineage and Idempotent Database Persistence
# -----------------------------------------------------------------------------

def test_deterministic_and_idempotent_creation():
    """
    Verifies that re-running/retrying for the same run_id preserves the existing
    incident identity and does not create duplicate rows.
    """
    db = get_test_db()
    mgr = IncidentManager(db)
    run_id = str(uuid.uuid4())

    # Pre-requisite: ensure a parent pipeline_runs record exists for foreign key
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pipeline_runs (run_id, source_filename, source_filepath, status)
                VALUES (%s, 'test.xlsx', '/data/test.xlsx', 'RUNNING')
                ON CONFLICT (run_id) DO NOTHING;
            """, (run_id,))
            conn.commit()
    finally:
        conn.close()

    try:
        failure = {
            "check_id": "REC-V01",
            "check_name": "Row sum cross-check",
            "table_name": "table_ii_state",
            "status": "FAIL",
            "severity": "ERROR",
            "expected_value": "100.0",
            "observed_value": "99.0",
            "difference": 1.0,
            "affected_records": 1
        }

        # First recording
        inc1 = mgr.create_incident(run_id, [failure])
        inc1_id = mgr.record_incident_in_db(inc1)
        assert inc1_id is not None
        assert inc1.incident_id == inc1_id

        # Second recording (simulating task retry for identical run_id)
        inc2 = mgr.create_incident(run_id, [failure])
        inc2_id = mgr.record_incident_in_db(inc2)

        # Must preserve original incident_id
        assert inc2_id == inc1_id
        assert inc2.incident_id == inc1_id

        # Verify only 1 record exists in DB
        retrieved = mgr.get_incident_by_run_id(run_id)
        assert retrieved is not None
        assert retrieved.incident_id == inc1_id
        assert retrieved.check_id == "REC-V01"
        assert retrieved.severity == IncidentSeverity.ERROR.value

    finally:
        # Cleanup
        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM pipeline_runs WHERE run_id = %s;", (run_id,))
                conn.commit()
        finally:
            conn.close()


# -----------------------------------------------------------------------------
# 5. Advisory Findings Do Not Create Blocking Incidents
# -----------------------------------------------------------------------------

def test_advisory_findings_do_not_create_blocking_incidents():
    """
    Verifies that non-blocking findings (OTHER TERRITORY UNRESOLVED,
    STATISTICALLY_DIFFERENT) are filtered out from blocking failures.
    """
    advisory_failures = [
        {
            "check_id": "REC-DO06",
            "rule_code": "REC-DO06",
            "rule_name": "State trade balance equality",
            "entity": "OTHER TERRITORY",
            "status": "UNRESOLVED",
            "severity": "WARNING",
            "message": "Inward movement differs by 3030.56 cr"
        },
        {
            "dimension": "STATE_OUTWARD",
            "metric": "KS_STATISTIC",
            "status": "STATISTICALLY_DIFFERENT",
            "severity": "INFO",
            "message": "Distribution shifted between FY22-23 and FY23-24"
        },
        {
            "check_id": "SCH-01",
            "status": "PASS",
            "severity": "INFO",
            "message": "Schema check passed"
        }
    ]

    blocking = IncidentManager.filter_blocking_failures(advisory_failures)
    assert len(blocking) == 0, "Advisory findings must not produce blocking failures."

    # If mixed with a real failure, only the real failure is retained
    real_failure = {
        "check_id": "DOM-01",
        "status": "FAIL",
        "severity": "CRITICAL",
        "message": "Invalid state code"
    }
    mixed = IncidentManager.filter_blocking_failures(advisory_failures + [real_failure])
    assert len(mixed) == 1
    assert mixed[0]["check_id"] == "DOM-01"


# -----------------------------------------------------------------------------
# 6. Incident Markdown File Audit
# -----------------------------------------------------------------------------

def test_incident_markdown_audit_file(tmp_path):
    """Verifies that write_incident_file generates a readable, well-structured markdown report."""
    run_id = str(uuid.uuid4())
    failure = {
        "check_id": "NUM-05",
        "table_name": "table_iii_outward",
        "status": "FAIL",
        "severity": "CRITICAL",
        "expected_value": "10.0",
        "observed_value": "20.0",
        "difference": 10.0,
        "message": "Movement discrepancy"
    }

    mgr = IncidentManager()
    incident = mgr.create_incident(run_id, [failure])
    incident.incident_id = 101

    out_file = mgr.write_incident_file(incident, output_dir=str(tmp_path))
    assert os.path.exists(out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "# Incident Report:" in content
    assert f"**Incident ID:** `101`" in content
    assert f"**Pipeline Run ID:** `{run_id}`" in content
    assert f"**Severity:** `CRITICAL`" in content
    assert "NUM-05" in content
    assert "table_iii_outward" in content
