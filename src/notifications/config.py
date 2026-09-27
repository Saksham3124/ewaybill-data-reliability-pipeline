"""
src/notifications/config.py
----------------------------
Configuration models for pipeline alert notifications.

Ensures:
- Secure reading from environment variables.
- Strict masking of secrets in strings, representations, and log outputs.
- Graceful defaults when notifications are disabled.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class NotificationConfig:
    """
    Configuration parameters for email alerting.
    
    All secrets (e.g. smtp_password) are masked in __repr__ to prevent exposure in logs.
    """
    alert_email_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    sender_email: str = "pipeline-alerts@example.com"
    recipient_emails: List[str] = field(default_factory=lambda: ["data-reliability-team@example.com"])

    @classmethod
    def from_env(cls) -> "NotificationConfig":
        """Loads configuration from environment variables with safe defaults."""
        enabled_str = os.getenv("ALERT_EMAIL_ENABLED", "false").lower()
        alert_email_enabled = enabled_str in ("true", "1", "yes")

        smtp_host = os.getenv("SMTP_HOST", "localhost")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER") or None
        smtp_password = os.getenv("SMTP_PASSWORD") or None

        tls_str = os.getenv("SMTP_USE_TLS", "true").lower()
        smtp_use_tls = tls_str in ("true", "1", "yes")

        sender_email = os.getenv("ALERT_SENDER_EMAIL", "pipeline-alerts@example.com")

        recipients_str = os.getenv("ALERT_RECIPIENT_EMAILS", "data-reliability-team@example.com")
        recipient_emails = [r.strip() for r in recipients_str.split(",") if r.strip()]

        return cls(
            alert_email_enabled=alert_email_enabled,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_use_tls=smtp_use_tls,
            sender_email=sender_email,
            recipient_emails=recipient_emails
        )

    def __repr__(self) -> str:
        """Sanitized representation concealing SMTP credentials."""
        masked_pwd = "********" if self.smtp_password else "None"
        return (
            f"NotificationConfig(enabled={self.alert_email_enabled}, "
            f"host='{self.smtp_host}:{self.smtp_port}', "
            f"user='{self.smtp_user}', password={masked_pwd}, "
            f"tls={self.smtp_use_tls}, sender='{self.sender_email}', "
            f"recipients={self.recipient_emails})"
        )
