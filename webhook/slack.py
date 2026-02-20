import requests
import os
import json
from datetime import datetime


class SlackNotifier:
    """Send alerts to Slack webhook."""

    def __init__(self, webhook_url=None):
        """
        Initialize Slack notifier.

        Args:
            webhook_url: Slack webhook URL (defaults to SLACK_WEBHOOK_URL env var)
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.enabled = bool(self.webhook_url)

    def send_alert(self, alert_name, alert_status, container_name=None, error=None):
        """
        Send alert notification to Slack.

        Args:
            alert_name: Name of the alert
            alert_status: Status of the alert (firing, resolved)
            container_name: Name of the container that was remediated
            error: Error message if remediation failed
        """
        if not self.enabled:
            return False

        try:
            color = "#FF0000" if alert_status == "firing" else "#00FF00"
            status_text = "🚨 FIRING" if alert_status == "firing" else "✅ RESOLVED"
            timestamp = datetime.now().isoformat()

            message = {
                "text": f"{status_text}: {alert_name}",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {"title": "Alert", "value": alert_name, "short": True},
                            {"title": "Status", "value": status_text, "short": True},
                            {
                                "title": "Timestamp",
                                "value": timestamp,
                                "short": False,
                            },
                        ],
                    }
                ],
            }

            if container_name:
                message["attachments"][0]["fields"].append(
                    {
                        "title": "Container Action",
                        "value": f"Restarted {container_name}",
                        "short": False,
                    }
                )

            if error:
                message["attachments"][0]["fields"].append(
                    {"title": "Error", "value": error, "short": False}
                )

            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=5,
            )

            return response.status_code == 200

        except Exception as e:
            print(f"Failed to send Slack notification: {e}")
            return False

    def send_remediation_message(self, alert_name, container_name, success=True):
        """
        Send remediation action message to Slack.

        Args:
            alert_name: Name of the alert
            container_name: Container that was restarted
            success: Whether remediation was successful
        """
        if not self.enabled:
            return False

        try:
            color = "#0099FF" if success else "#FF6600"
            result = "✓ Success" if success else "✗ Failed"

            message = {
                "text": f"🔧 Remediation: {result}",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {"title": "Alert", "value": alert_name, "short": True},
                            {
                                "title": "Container",
                                "value": container_name,
                                "short": True,
                            },
                            {
                                "title": "Action",
                                "value": "Container Restarted",
                                "short": False,
                            },
                        ],
                    }
                ],
            }

            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=5,
            )

            return response.status_code == 200

        except Exception as e:
            print(f"Failed to send Slack remediation message: {e}")
            return False
