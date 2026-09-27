"""
src/notifications/__init__.py
------------------------------
Notification and alerting services for pipeline incidents.
"""

from src.notifications.config import NotificationConfig
from src.notifications.email_service import EmailAlertNotifier

__all__ = ["NotificationConfig", "EmailAlertNotifier"]
