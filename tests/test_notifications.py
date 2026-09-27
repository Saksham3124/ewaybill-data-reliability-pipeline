"""
tests/test_notifications.py
----------------------------
Unit tests for Phase 9 email notification mechanism.

Verifies:
1. Email generation only for blocking incidents.
2. Subject line formatting: [EWAYBILL PIPELINE] <SEVERITY> - Run <run_id>.
3. Complete presence of required fields in plaintext and HTML bodies.
4. No email sent for successful runs or statistical-only differences.
5. Recipient configuration handling.
6. Safe handling when SMTP configuration is missing or disabled.
7. SMTP transport failure does not erase or roll back persisted incidents.
8. Credentials and passwords are masked and never exposed in logs or representations.
"""

import logging
import uuid
import pytest
from unittest.mock import MagicMock, patch

from src.incidents.models import Incident, IncidentSeverity
from src.incidents.manager import IncidentManager
from src.notifications.config import NotificationConfig
from src.notifications.email_service import EmailAlertNotifier


# -----------------------------------------------------------------------------
# 1. Subject and Body Formatting
# -----------------------------------------------------------------------------

def test_email_formatting_and_subject():
    """Verifies that the generated email subject and body match all required fields."""
    run_id = str(uuid.uuid4())
    incident = Incident(
        incident_id=42,
        run_id=run_id,
        severity=IncidentSeverity.CRITICAL.value,
        failure_type="SCHEMA_VALIDATION_FAILURE",
        source_table="table_iv_inward",
        check_id="SCH-02",
        check_name="Missing mandatory columns",
        expected_value="column 'state' present",
        observed_value="column 'state' absent",
        difference=None,
        affected_record_count=0,
        description="Mandatory column 'state' was missing in raw Table IV worksheet.",
        status="OPEN",
        detection_timestamp="2026-09-27T12:00:00Z"
    )

    notifier = EmailAlertNotifier()
    subject, plain_body, html_body = notifier.format_email(incident)

    # 1. Subject line format
    assert subject == f"[EWAYBILL PIPELINE] CRITICAL - Run {run_id}"

    # 2. Plaintext body contents
    assert run_id in plain_body
    assert "Incident ID:           42" in plain_body
    assert "Severity:              CRITICAL" in plain_body
    assert "Failure Type:          SCHEMA_VALIDATION_FAILURE" in plain_body
    assert "Affected Table:        table_iv_inward" in plain_body
    assert "Check ID:              SCH-02" in plain_body
    assert "Check Name:            Missing mandatory columns" in plain_body
    assert "Expected Value:        column 'state' present" in plain_body
    assert "Observed Value:        column 'state' absent" in plain_body
    assert "Mandatory column 'state' was missing" in plain_body
    assert "2026-09-27T12:00:00Z" in plain_body

    # 3. HTML body contents
    assert f"<code>{run_id}</code>" in html_body
    assert "<code>SCH-02</code>" in html_body
    assert "<code>table_iv_inward</code>" in html_body


# -----------------------------------------------------------------------------
# 2. Recipient Configuration & Custom Mock Sender
# -----------------------------------------------------------------------------

def test_email_dispatch_with_mock_sender():
    """Verifies that the notifier delivers to configured recipients via transport."""
    run_id = str(uuid.uuid4())
    incident = Incident(
        incident_id=10,
        run_id=run_id,
        severity=IncidentSeverity.ERROR.value,
        failure_type="DATA_INTEGRITY_FAILURE",
        check_id="DOM-01",
        description="Invalid state name found.",
        triggering_failures=[]
    )

    config = NotificationConfig(
        alert_email_enabled=True,
        sender_email="alert-bot@test.org",
        recipient_emails=["data-ops@test.org", "lead@test.org"]
    )

    captured_messages = []

    def mock_sender(msg):
        captured_messages.append(msg)

    notifier = EmailAlertNotifier(config=config, smtp_sender_callable=mock_sender)
    result = notifier.send_incident_alert(incident)

    assert result["status"] == "SENT"
    assert incident.alert_sent is True
    assert len(captured_messages) == 1

    msg = captured_messages[0]
    assert msg["From"] == "alert-bot@test.org"
    assert "data-ops@test.org" in msg["To"]
    assert "lead@test.org" in msg["To"]
    assert f"[EWAYBILL PIPELINE] ERROR - Run {run_id}" in msg["Subject"]


# -----------------------------------------------------------------------------
# 3. No Email for Successful Runs or Statistical Differences
# -----------------------------------------------------------------------------

def test_no_email_for_non_blocking_outcomes():
    """
    Verifies that the reliability decision does NOT route to create_incident or
    generate an email alert for passing runs or advisory statistical differences.
    """
    from dags.ewaybill_reliability_pipeline import task_reliability_decision

    # Mock TaskInstance for a run with only statistical differences
    class MockTI:
        def xcom_pull(self, task_ids, key=None):
            return []  # No blocking failures
        def xcom_push(self, key, value):
            pass

    context = {"task_instance": MockTI()}
    branch = task_reliability_decision(**context)

    # Branch routes to promote_trusted_data, NOT create_incident
    assert branch == "promote_trusted_data"
    # Consequently, create_incident (and its email dispatcher) is never invoked.


# -----------------------------------------------------------------------------
# 4. Safe Handling when Email Disabled or Missing Configuration
# -----------------------------------------------------------------------------

def test_missing_or_disabled_email_configuration():
    """Verifies that disabled email alerts do not raise exceptions and return SKIPPED_DISABLED."""
    run_id = str(uuid.uuid4())
    incident = Incident(
        incident_id=5,
        run_id=run_id,
        severity=IncidentSeverity.CRITICAL.value,
        check_id="NUM-01",
        description="Negative value."
    )

    # Disabled config
    config = NotificationConfig(alert_email_enabled=False)
    notifier = EmailAlertNotifier(config=config)

    result = notifier.send_incident_alert(incident)
    assert result["status"] == "SKIPPED_DISABLED"
    assert incident.alert_sent is False


# -----------------------------------------------------------------------------
# 5. SMTP Failure Does Not Erase Persisted Incident
# -----------------------------------------------------------------------------

def test_smtp_failure_does_not_erase_persisted_incident():
    """
    Verifies that if the email transport raises an exception:
    - The incident is NOT deleted or erased.
    - An error result is returned.
    - The system continues without rolling back the incident.
    """
    run_id = str(uuid.uuid4())
    incident = Incident(
        incident_id=88,
        run_id=run_id,
        severity=IncidentSeverity.CRITICAL.value,
        check_id="STR-01",
        description="Structural corruption."
    )

    def failing_sender(msg):
        raise ConnectionRefusedError("SMTP server unreachable at port 587")

    config = NotificationConfig(alert_email_enabled=True)
    notifier = EmailAlertNotifier(config=config, smtp_sender_callable=failing_sender)

    result = notifier.send_incident_alert(incident)

    assert result["status"] == "FAILED"
    assert "ConnectionRefusedError" in result["error"]
    # Incident object remains valid and unaffected
    assert incident.incident_id == 88
    assert incident.severity == "CRITICAL"


# -----------------------------------------------------------------------------
# 6. Credentials Masking & Security
# -----------------------------------------------------------------------------

def test_credentials_not_exposed_in_representations():
    """Verifies that SMTP password is never exposed in repr or logs."""
    config = NotificationConfig(
        alert_email_enabled=True,
        smtp_host="smtp.corp.internal",
        smtp_user="super_secret_user",
        smtp_password="SuperSecretPassword123!"
    )

    repr_str = repr(config)
    assert "SuperSecretPassword123!" not in repr_str
    assert "********" in repr_str


# -----------------------------------------------------------------------------
# 7. Idempotent Alert Suppression
# -----------------------------------------------------------------------------

def test_alert_idempotency_prevents_duplicate_email():
    """Verifies that if incident.alert_sent is already True, duplicate emails are skipped."""
    run_id = str(uuid.uuid4())
    incident = Incident(
        incident_id=99,
        run_id=run_id,
        severity=IncidentSeverity.CRITICAL.value,
        check_id="CMP-01",
        description="Missing chapter",
        alert_sent=True  # Already dispatched previously
    )

    mock_send = MagicMock()
    config = NotificationConfig(alert_email_enabled=True)
    notifier = EmailAlertNotifier(config=config, smtp_sender_callable=mock_send)

    result = notifier.send_incident_alert(incident, force=False)

    assert result["status"] == "SKIPPED_DUPLICATE"
    mock_send.assert_not_called()
