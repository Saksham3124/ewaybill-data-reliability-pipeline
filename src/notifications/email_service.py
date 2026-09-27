"""
src/notifications/email_service.py
-----------------------------------
Email alerting service for blocking pipeline incidents.

Adheres strictly to the architectural rules:
- Only sends email when a blocking incident is created.
- Formats subject as: [EWAYBILL PIPELINE] <SEVERITY> - Run <run_id>.
- Includes all required failure diagnostics in plaintext and HTML formats.
- Never logs or exposes passwords, API keys, or SMTP secrets.
- Idempotently prevents duplicate alerts for the same incident/run.
- Non-fatal to incident persistence: an email delivery failure leaves the incident
  authoritatively recorded in PostgreSQL and merely logs a diagnostic warning.
"""

import email.message
import logging
import smtplib
from typing import Dict, Any, Optional, Tuple, Callable

from src.incidents.models import Incident
from src.incidents.manager import IncidentManager
from src.notifications.config import NotificationConfig

logger = logging.getLogger(__name__)


class EmailAlertNotifier:
    """Dispatches email alerts when blocking data-integrity incidents occur."""

    def __init__(
        self,
        config: Optional[NotificationConfig] = None,
        incident_manager: Optional[IncidentManager] = None,
        smtp_sender_callable: Optional[Callable[[email.message.EmailMessage], None]] = None
    ):
        self.config = config or NotificationConfig.from_env()
        self.incident_manager = incident_manager
        self.custom_sender = smtp_sender_callable

    def format_email(self, incident: Incident) -> Tuple[str, str, str]:
        """
        Constructs the email subject, plaintext body, and HTML body from the incident.
        
        Returns:
            Tuple[subject, plaintext_body, html_body]
        """
        severity = incident.severity.upper()
        subject = f"[EWAYBILL PIPELINE] {severity} - Run {incident.run_id}"

        # Diagnostics extraction with NULL preservation
        inc_id_str = str(incident.incident_id) if incident.incident_id is not None else "UNSAVED"
        table_str = incident.source_table or "N/A"
        check_id_str = incident.check_id or "N/A"
        check_name_str = incident.check_name or "N/A"
        expected_str = incident.expected_value if incident.expected_value is not None else "N/A"
        observed_str = incident.observed_value if incident.observed_value is not None else "N/A"
        diff_str = f"{incident.difference:,.4f}" if incident.difference is not None else "N/A"
        records_str = f"{incident.affected_record_count:,}" if incident.affected_record_count else "0"
        timestamp_str = incident.detection_timestamp or "N/A"
        status_str = incident.status

        # Plaintext body
        text_lines = [
            f"=== E-WAY BILL DATA RELIABILITY INCIDENT ===",
            f"",
            f"Pipeline Run ID:       {incident.run_id}",
            f"Incident ID:           {inc_id_str}",
            f"Severity:              {severity}",
            f"Action / Status:       {status_str}",
            f"Failure Type:          {incident.failure_type}",
            f"Affected Table:        {table_str}",
            f"Check ID:              {check_id_str}",
            f"Check Name:            {check_name_str}",
            f"Expected Value:        {expected_str}",
            f"Observed Value:        {observed_str}",
            f"Difference:            {diff_str}",
            f"Affected Records:      {records_str}",
            f"Detection Timestamp:   {timestamp_str}",
            f"",
            f"--- Failure Description ---",
            f"{incident.description}",
            f"",
            f"Action Taken: Trusted warehouse loading was halted immediately.",
            f"Please inspect docs/incidents/incident_{incident.run_id}.md or query PostgreSQL table 'incidents'."
        ]

        if len(incident.triggering_failures) > 1:
            text_lines.append("")
            text_lines.append(f"Total Underlying Failures: {len(incident.triggering_failures)}")
            for idx, f in enumerate(incident.triggering_failures[:5], 1):
                cid = f.get("check_id") or f.get("rule_code") or "N/A"
                tbl = f.get("table_name") or f.get("source_tables") or "N/A"
                msg = f.get("message") or ""
                text_lines.append(f"  {idx}. [{cid}] {tbl}: {msg}")
            if len(incident.triggering_failures) > 5:
                text_lines.append(f"  ... and {len(incident.triggering_failures) - 5} more failures.")

        plaintext_body = "\n".join(text_lines)

        # HTML body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #333;">
            <div style="background-color: {'#d9534f' if severity == 'CRITICAL' else '#f0ad4e'}; color: white; padding: 12px; border-radius: 4px;">
                <h2 style="margin: 0;">E-Way Bill Data Reliability Incident: {severity}</h2>
            </div>
            <p><strong>Pipeline Run ID:</strong> <code>{incident.run_id}</code><br>
               <strong>Incident ID:</strong> <code>{inc_id_str}</code><br>
               <strong>Action / Status:</strong> <code>{status_str}</code></p>
            
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; border-color: #ddd;">
                <tr style="background-color: #f7f7f7;">
                    <th align="left" style="width: 25%;">Field</th>
                    <th align="left">Details</th>
                </tr>
                <tr><td><strong>Failure Type</strong></td><td>{incident.failure_type}</td></tr>
                <tr><td><strong>Affected Table</strong></td><td><code>{table_str}</code></td></tr>
                <tr><td><strong>Check ID</strong></td><td><code>{check_id_str}</code></td></tr>
                <tr><td><strong>Check Name</strong></td><td>{check_name_str}</td></tr>
                <tr><td><strong>Expected Value</strong></td><td><code>{expected_str}</code></td></tr>
                <tr><td><strong>Observed Value</strong></td><td><code>{observed_str}</code></td></tr>
                <tr><td><strong>Difference</strong></td><td><code>{diff_str}</code></td></tr>
                <tr><td><strong>Affected Records</strong></td><td>{records_str}</td></tr>
                <tr><td><strong>Timestamp</strong></td><td>{timestamp_str}</td></tr>
            </table>

            <h3>Failure Description</h3>
            <p style="background-color: #f9f9f9; padding: 10px; border-left: 4px solid #d9534f;">
                {incident.description}
            </p>
            <p><strong>Action Taken:</strong> Promotion to trusted warehouse tables was halted.</p>
        </body>
        </html>
        """

        return subject, plaintext_body, html_body

    def send_incident_alert(self, incident: Incident, force: bool = False) -> Dict[str, Any]:
        """
        Dispatches an email alert for a blocking incident.
        
        Idempotency:
        - If incident.alert_sent is True and not force, skips sending to prevent alert duplication.
        
        Failure Policy:
        - Notification failure is secondary; does NOT delete or roll back the incident.
        - Catches network/SMTP errors and logs sanitized diagnostic message.
        """
        # Idempotency check: don't re-alert for same incident
        if incident.alert_sent and not force:
            logger.info(f"Alert already sent for incident #{incident.incident_id} (run {incident.run_id}). Skipping duplicate dispatch.")
            return {
                "status": "SKIPPED_DUPLICATE",
                "incident_id": incident.incident_id,
                "run_id": incident.run_id
            }

        subject, text_body, html_body = self.format_email(incident)

        # Check if email is enabled
        if not self.config.alert_email_enabled and not self.custom_sender:
            logger.info("Email alerting is disabled (ALERT_EMAIL_ENABLED=false). Alert recorded without dispatch.")
            return {
                "status": "SKIPPED_DISABLED",
                "subject": subject,
                "recipients": self.config.recipient_emails,
                "text_body": text_body
            }

        # Build email message
        msg = email.message.EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.config.sender_email
        msg["To"] = ", ".join(self.config.recipient_emails)
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")

        # Custom mock sender (used in testing or customized transport)
        if self.custom_sender:
            try:
                self.custom_sender(msg)
                incident.alert_sent = True
                if self.incident_manager and incident.incident_id:
                    self.incident_manager.mark_alert_sent(incident.incident_id)
                return {
                    "status": "SENT",
                    "subject": subject,
                    "recipients": self.config.recipient_emails,
                    "transport": "custom"
                }
            except Exception as e:
                logger.error(f"Custom email sender failed for run {incident.run_id}: {e}")
                return {
                    "status": "FAILED",
                    "error": f"{type(e).__name__}: {str(e)}",
                    "transport": "custom"
                }

        # Real SMTP transport
        try:
            logger.info(f"Connecting to SMTP server at {self.config.smtp_host}:{self.config.smtp_port}...")
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=15) as server:
                if self.config.smtp_use_tls:
                    server.starttls()
                if self.config.smtp_user and self.config.smtp_password:
                    server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)

            incident.alert_sent = True
            if self.incident_manager and incident.incident_id:
                self.incident_manager.mark_alert_sent(incident.incident_id)

            logger.info(f"Email alert successfully dispatched to {len(self.config.recipient_emails)} recipient(s).")
            return {
                "status": "SENT",
                "subject": subject,
                "recipients": self.config.recipient_emails,
                "transport": "smtp"
            }
        except Exception as e:
            # Safely log error without printing passwords
            logger.error(f"SMTP delivery failed for run {incident.run_id} to host {self.config.smtp_host}: {type(e).__name__}: {e}")
            return {
                "status": "FAILED",
                "error": f"{type(e).__name__}: {str(e)}",
                "transport": "smtp"
            }
