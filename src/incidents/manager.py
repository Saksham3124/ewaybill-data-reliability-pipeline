"""
src/incidents/manager.py
------------------------
Incident manager for recording, formatting, and persisting reliability pipeline incidents.

Enforces:
- Deterministic severity aggregation (CRITICAL > ERROR > WARNING).
- Idempotent incident persistence (preserves incident ID and prevents duplicates on rerun/retry).
- Exact lineage preservation using run_id as primary lineage key.
- Safe extraction of underlying failure metrics (expected, observed, difference, affected records).
- Strict exclusion of non-blocking advisory findings from blocking incident creation.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.database.connection import DatabaseManager
from src.incidents.models import Incident, IncidentSeverity, IncidentStatus

logger = logging.getLogger(__name__)


class IncidentManager:
    """Manages failure incidents when data reliability gates fail."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager

    @staticmethod
    def filter_blocking_failures(failures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filters out non-blocking items (e.g. advisory reconciliation UNRESOLVED or statistical shifts)
        and retains only blocking data integrity failures.
        """
        blocking = []
        for f in failures:
            status = str(f.get("status", "")).upper()
            severity = str(f.get("severity", "")).upper()
            # Status must be FAIL and severity ERROR or CRITICAL to be blocking
            if status == "FAIL" and severity in ("CRITICAL", "ERROR"):
                blocking.append(f)
        return blocking

    def create_incident(
        self,
        run_id: str,
        failures: List[Dict[str, Any]],
        incident_type: str = "DATA_INTEGRITY_FAILURE",
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Incident:
        """
        Constructs an Incident record from triggering validation/reconciliation failures.
        
        Aggregation Policy:
        - Evaluates highest severity among failures: CRITICAL > ERROR > WARNING.
        - Extracts primary check and table details from the most severe failure.
        - Aggregates affected record counts across all underlying failures.
        - Preserves all underlying failure records in triggering_failures payload.
        """
        if not failures:
            # Fallback for empty or unknown failure list
            return Incident(
                run_id=run_id,
                severity=IncidentSeverity.ERROR.value,
                failure_type=incident_type,
                title=title or "Data Reliability Gate Failure",
                description=description or f"Pipeline run {run_id} failed reliability checks.",
                triggering_failures=[],
                detection_timestamp=datetime.now(timezone.utc).isoformat()
            )

        # Sort failures to find primary (CRITICAL first, then ERROR, then WARNING)
        severity_order = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "INFO": 3}
        sorted_failures = sorted(
            failures,
            key=lambda f: severity_order.get(str(f.get("severity", "")).upper(), 99)
        )
        primary = sorted_failures[0]

        # Determine overall severity
        primary_sev_str = str(primary.get("severity", "ERROR")).upper()
        if primary_sev_str == "CRITICAL":
            highest_sev = IncidentSeverity.CRITICAL.value
        elif primary_sev_str == "ERROR":
            highest_sev = IncidentSeverity.ERROR.value
        else:
            highest_sev = IncidentSeverity.WARNING.value

        # Extract primary failure attributes (without inventing values)
        primary_table = primary.get("table_name") or primary.get("source_tables") or None
        primary_check_id = primary.get("check_id") or primary.get("rule_code") or None
        primary_check_name = primary.get("check_name") or primary.get("rule_name") or primary.get("message") or None

        expected_val = primary.get("expected_value")
        expected_str = str(expected_val) if expected_val is not None else None

        observed_val = primary.get("observed_value")
        observed_str = str(observed_val) if observed_val is not None else None

        diff_val = primary.get("difference") or primary.get("absolute_difference")
        diff_float = float(diff_val) if diff_val is not None else None

        total_affected = sum(int(f.get("affected_records", 0)) for f in failures if f.get("affected_records") is not None)

        fail_names = [f.get("check_id") or f.get("rule_code") for f in sorted_failures]
        distinct_ids = list(dict.fromkeys(filter(None, fail_names)))
        default_title = f"Data Reliability Gate Failure: {', '.join(distinct_ids[:3])}"
        if len(distinct_ids) > 3:
            default_title += f" (+{len(distinct_ids) - 3} more)"

        default_desc = (
            f"Pipeline run {run_id} failed reliability validation with {len(failures)} "
            f"integrity check(s). Primary failure: [{primary_check_id}] in {primary_table or 'source'}. "
            f"Promotion to trusted warehouse was halted."
        )

        incident = Incident(
            run_id=run_id,
            severity=highest_sev,
            failure_type=incident_type,
            source_table=primary_table,
            check_id=primary_check_id,
            check_name=primary_check_name,
            expected_value=expected_str,
            observed_value=observed_str,
            difference=diff_float,
            affected_record_count=total_affected,
            title=title or default_title,
            description=description or default_desc,
            triggering_failures=failures,
            status=IncidentStatus.OPEN.value,
            detection_timestamp=datetime.now(timezone.utc).isoformat()
        )

        return incident

    def record_incident_in_db(self, incident: Incident) -> Optional[int]:
        """
        Idempotently persists the incident in PostgreSQL.
        
        If an incident for this run_id already exists:
        - Preserves the existing incident_id and detection_timestamp.
        - Syncs incident attributes from DB (including alert_sent status).
        - Prevents duplicate incident records.
        """
        if not self.db:
            return None

        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                # 1. Check if incident for run_id already exists
                cur.execute("""
                    SELECT incident_id, severity, status, failure_type, source_table,
                           check_id, check_name, expected_value, observed_value, difference,
                           affected_record_count, detection_timestamp, resolution_timestamp,
                           resolution_notes, alert_sent, alert_sent_at, title, description,
                           triggering_failures
                    FROM incidents
                    WHERE run_id = %s;
                """, (incident.run_id,))
                row = cur.fetchone()

                if row:
                    # Incident already exists for this run_id: preserve identity and state
                    incident.incident_id = row[0]
                    incident.severity = row[1]
                    incident.status = row[2]
                    incident.failure_type = row[3]
                    incident.source_table = row[4]
                    incident.check_id = row[5]
                    incident.check_name = row[6]
                    incident.expected_value = row[7]
                    incident.observed_value = row[8]
                    incident.difference = float(row[9]) if row[9] is not None else None
                    incident.affected_record_count = row[10] or 0
                    incident.detection_timestamp = row[11].isoformat() if row[11] else incident.detection_timestamp
                    incident.resolution_timestamp = row[12].isoformat() if row[12] else None
                    incident.resolution_notes = row[13]
                    incident.alert_sent = row[14]
                    incident.alert_sent_at = row[15].isoformat() if row[15] else None
                    incident.title = row[16]
                    incident.description = row[17]
                    logger.info(f"Preserving existing incident #{incident.incident_id} for run {incident.run_id}")
                    return incident.incident_id

                # 2. Insert new incident record
                cur.execute("""
                    INSERT INTO incidents (
                        run_id, incident_type, failure_type, severity, status,
                        source_table, check_id, check_name, expected_value,
                        observed_value, difference, affected_record_count,
                        title, description, triggering_failures,
                        detection_timestamp, created_at, alert_sent
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s
                    )
                    RETURNING incident_id;
                """, (
                    incident.run_id,
                    incident.failure_type,
                    incident.failure_type,
                    incident.severity,
                    incident.status,
                    incident.source_table,
                    incident.check_id,
                    incident.check_name,
                    incident.expected_value,
                    incident.observed_value,
                    incident.difference,
                    incident.affected_record_count,
                    incident.title,
                    incident.description,
                    json.dumps(incident.triggering_failures),
                    incident.detection_timestamp,
                    incident.detection_timestamp,
                    incident.alert_sent
                ))
                inc_id = cur.fetchone()[0]
                conn.commit()
                incident.incident_id = inc_id
                logger.info(f"Created new incident #{incident.incident_id} for run {incident.run_id}")
                return inc_id
        finally:
            conn.close()

    def mark_alert_sent(self, incident_id: int) -> None:
        """Marks an incident's alert as dispatched in the database."""
        if not self.db or not incident_id:
            return

        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE incidents
                    SET alert_sent = TRUE,
                        alert_sent_at = NOW()
                    WHERE incident_id = %s;
                """, (incident_id,))
                conn.commit()
        finally:
            conn.close()

    def get_incident_by_run_id(self, run_id: str) -> Optional[Incident]:
        """Retrieves an incident record for a specific run_id."""
        if not self.db:
            return None

        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT incident_id, run_id, severity, status, failure_type,
                           source_table, check_id, check_name, expected_value,
                           observed_value, difference, affected_record_count,
                           title, description, triggering_failures,
                           detection_timestamp, resolution_timestamp, resolution_notes,
                           alert_sent, alert_sent_at
                    FROM incidents
                    WHERE run_id = %s;
                """, (run_id,))
                row = cur.fetchone()
                if not row:
                    return None

                return Incident(
                    incident_id=row[0],
                    run_id=str(row[1]),
                    severity=row[2],
                    status=row[3],
                    failure_type=row[4],
                    source_table=row[5],
                    check_id=row[6],
                    check_name=row[7],
                    expected_value=row[8],
                    observed_value=row[9],
                    difference=float(row[10]) if row[10] is not None else None,
                    affected_record_count=row[11] or 0,
                    title=row[12],
                    description=row[13],
                    triggering_failures=row[14] if isinstance(row[14], list) else (json.loads(row[14]) if row[14] else []),
                    detection_timestamp=row[15].isoformat() if row[15] else None,
                    resolution_timestamp=row[16].isoformat() if row[16] else None,
                    resolution_notes=row[17],
                    alert_sent=row[18],
                    alert_sent_at=row[19].isoformat() if row[19] else None
                )
        finally:
            conn.close()

    def write_incident_file(self, incident: Incident, output_dir: str = "docs/incidents") -> str:
        """Writes a formatted markdown incident file for audit trail."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / f"incident_{incident.run_id}.md"

        md = [
            f"# Incident Report: {incident.title}",
            "",
            f"- **Incident ID:** `{incident.incident_id or 'UNSAVED'}`",
            f"- **Pipeline Run ID:** `{incident.run_id}`",
            f"- **Severity:** `{incident.severity}`",
            f"- **Status:** `{incident.status}`",
            f"- **Failure Type:** `{incident.failure_type}`",
            f"- **Primary Table:** `{incident.source_table or 'N/A'}`",
            f"- **Primary Check ID:** `{incident.check_id or 'N/A'}`",
            f"- **Primary Check Name:** {incident.check_name or 'N/A'}",
            f"- **Expected Value:** `{incident.expected_value or 'N/A'}`",
            f"- **Observed Value:** `{incident.observed_value or 'N/A'}`",
            f"- **Difference:** `{incident.difference if incident.difference is not None else 'N/A'}`",
            f"- **Affected Records:** `{incident.affected_record_count}`",
            f"- **Detection Timestamp:** `{incident.detection_timestamp}`",
            f"- **Resolution Timestamp:** `{incident.resolution_timestamp or 'OPEN'}`",
            f"- **Alert Sent:** `{incident.alert_sent}`",
            "",
            "## Description",
            f"{incident.description}",
            "",
            "## All Triggering Failures",
            "",
            "| Check ID | Table | Status | Severity | Expected | Observed | Diff | Message |",
            "| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |"
        ]

        for f in incident.triggering_failures:
            cid = f.get("check_id") or f.get("rule_code") or "N/A"
            tbl = f.get("table_name") or f.get("source_tables") or "N/A"
            stat = f.get("status") or "FAIL"
            sev = f.get("severity") or "ERROR"
            exp = str(f.get("expected_value")) if f.get("expected_value") is not None else "N/A"
            obs = str(f.get("observed_value")) if f.get("observed_value") is not None else "N/A"
            diff = str(f.get("difference")) if f.get("difference") is not None else (str(f.get("absolute_difference")) if f.get("absolute_difference") is not None else "N/A")
            msg = f.get("message") or ""
            md.append(f"| `{cid}` | `{tbl}` | `{stat}` | `{sev}` | `{exp}` | `{obs}` | `{diff}` | {msg} |")

        md.append("")
        content = "\n".join(md) + "\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)
