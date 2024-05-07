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
        self.ntfy_token = cast(str, self.get_config_option("token"))
        self.ntfy_topic = cast(str, self.get_config_option("topic", required=True))
        self.ntfy_server = cast(
            str, self.get_config_option("server", default="https://ntfy.sh")
        )
        self.ntfy_priority = cast(
            str,
            self.get_config_option(
                "priority",
                required_type="str",
                allowed_values=[
                    "max",
                    "urgent",
                    "high",
                    "default",
                    "low",
                    "min",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                ],
                default="default",
            ),
        )
        self.ntfy_tags = cast(str, self.get_config_option("tags", required_type="str"))
        self.timeout = cast(
            int, self.get_config_option("timeout", required_type="int", default=5)
        )
        self.support_catchup = True
        # prefix icon to subject
        self.ntfy_icon_prefix = cast(
            str,
            self.get_config_option("icon_prefix", required_type="bool", default=False),
        )
        self.ntfy_icon_failed = chr(
            int(
                cast(
                    str,
                    self.get_config_option(
                        "icon_failed", required_type="str", default="274C"
                    ),
                ),
                16,
            )
        )
        self.ntfy_icon_succeeded = chr(
            int(
                cast(
                    str,
                    self.get_config_option(
                        "icon_succeeded", required_type="str", default="2705"
                    ),
                ),
                16,
            )
        )

    def send_ntfy_notification(self, subject: str, body: str) -> None:
        """Send a push notification."""
        requests.post(
            f"{self.ntfy_server}/{self.ntfy_topic}",
            data=body,
            headers={
                "Title": subject.encode("UTF-8"),
                "Priority": self.ntfy_priority,
                **({"Tags": self.ntfy_tags} if self.ntfy_tags else {}),
                **(
                    {"Authorization": f"Bearer {self.ntfy_token}"}
                    if self.ntfy_token
                    else {}
                ),
            },
            timeout=self.timeout,
        )

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Build up the content for the push notification."""

        alert_type = self.should_alert(monitor)

        if alert_type == AlertType.NONE:
            return
        subject = self.build_message(AlertLength.NOTIFICATION, alert_type, monitor)
        body = self.build_message(AlertLength.FULL, alert_type, monitor)

        # prefix icon to subject when relevant
        if self.ntfy_icon_prefix and subject.endswith("failed"):
            subject = f"{self.ntfy_icon_failed} {subject}"
        if self.ntfy_icon_prefix and subject.endswith("succeeded"):
            subject = f"{self.ntfy_icon_succeeded} {subject}"

        if not self._dry_run:
            try:
                self.send_ntfy_notification(subject, body)
            except Exception:
                self.alerter_logger.exception("Couldn't send ntfy notification")
        else:
            self.alerter_logger.info("dry_run: would send nfty notification: %s", body)

    def _describe_action(self) -> str:
        return f"posting to ntfy topic {self.ntfy_topic}"
