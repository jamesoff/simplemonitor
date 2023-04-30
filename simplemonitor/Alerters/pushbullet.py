"""
SimpleMonitor alerts via pushbullet
"""

from typing import cast

import requests
import requests.auth

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class PushbulletAlerter(Alerter):
    """Send push notification via Pushbullet."""

    alerter_type = "pushbullet"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        self.pushbullet_token = cast(
            str, self.get_config_option("token", required=True, allow_empty=False)
        )
        self.timeout = cast(
            int, self.get_config_option("timeout", required_type="int", default=5)
        )

        self.support_catchup = True

    def send_pushbullet_notification(self, subject: str, body: str) -> None:
        """Send a push notification."""
        _payload = {"type": "note", "title": subject, "body": body}
        _auth = requests.auth.HTTPBasicAuth(self.pushbullet_token, "")

        response = requests.post(
            "https://api.pushbullet.com/v2/pushes",
            data=_payload,
            auth=_auth,
            timeout=self.timeout,
        )
        if not response.status_code == requests.codes.ok:
            raise RuntimeError("Unable to send Pushbullet notification")

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Build up the content for the push notification."""

        alert_type = self.should_alert(monitor)
        if alert_type == AlertType.NONE:
            return

        subject = self.build_message(AlertLength.NOTIFICATION, alert_type, monitor)
        body = self.build_message(AlertLength.FULL, alert_type, monitor)

        if not self._dry_run:
            try:
                self.send_pushbullet_notification(subject, body)
            except Exception:
                self.alerter_logger.exception("Couldn't send push notification")
        else:
            self.alerter_logger.info("dry_run: would send push notification: %s", body)

    def _describe_action(self) -> str:
        return "posting to pushbullet"
