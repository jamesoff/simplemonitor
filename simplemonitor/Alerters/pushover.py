# coding=utf-8
from typing import cast

import requests

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class PushoverAlerter(Alerter):
    """Send push notification via Pushover."""

    alerter_type = "pushover"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)

        self.pushover_token = cast(
            str, self.get_config_option("token", required=True, allow_empty=False)
        )
        self.pushover_user = cast(
            str, self.get_config_option("user", required=True, allow_empty=False)
        )

        self.support_catchup = True

    def send_pushover_notification(self, subject: str, body: str) -> None:
        """Send a push notification."""

        requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": self.pushover_token,
                "user": self.pushover_user,
                "title": subject,
                "message": body,
            },
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
                self.send_pushover_notification(subject, body)
            except Exception:
                self.alerter_logger.exception("Couldn't send push notification")
                self.available = False
        else:
            self.alerter_logger.info("dry_run: would send push notification: %s", body)
