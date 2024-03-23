"""
SimpleMonitor alerts via ntfy
"""

from typing import cast

import requests

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class NtfyAlerter(Alerter):
    """Send push notification via ntfy."""

    alerter_type = "ntfy"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        self.ntfy_token = cast(
            str, self.get_config_option("token",default="")
        )
        self.ntfy_topic = cast(
            str, self.get_config_option("topic",required=True )
        )
        self.ntfy_server = cast(
            str, self.get_config_option("server", default="https://ntfy.sh")
        )
        self.ntfy_priority = cast(
            str, self.get_config_option("priority", default="default")
        )
        self.ntfy_tags = cast(
            int, self.get_config_option("tags", default="")
        )
        self.timeout = cast(
            int, self.get_config_option("timeout", required_type="int", default=5)
        )

        self.support_catchup = True

    def send_ntfy_notification(self, subject: str, body: str) -> None:
        """Send a push notification."""
        requests.post(
            f"{self.ntfy_server}/{self.ntfy_topic}",
            data=body,
            headers={
                    "Title": subject,
                    "Priority": self.ntfy_priority,
                    "Tags": self.ntfy_tags,
                    "Authorization": f"Bearer {self.ntfy_token}"
                },

            timeout=self.timeout
        )

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Build up the content for the push notification."""

        alert_type = self.should_alert(monitor)

        if alert_type == AlertType.NONE:
            return
        subject = self.build_message(AlertLength.NOTIFICATION, alert_type, monitor)
        body = self.build_message(AlertLength.FULL, alert_type, monitor)

        if not self._dry_run:
            try:
                self.send_ntfy_notification(subject, body)
            except Exception:
                self.alerter_logger.exception("Couldn't send ntfy notification")
        else:
            self.alerter_logger.info("dry_run: would send nfty notification: %s", body)

    def _describe_action(self) -> str:
        return "posting to ntfy"
