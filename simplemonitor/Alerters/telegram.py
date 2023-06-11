"""
SimpleMonitor alerts via Telegram
"""

from typing import cast

import requests

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class TelegramAlerter(Alerter):
    """Send push notification via Telegram."""

    alerter_type = "telegram"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)

        self.telegram_token = cast(
            str, self.get_config_option("token", required=True, allow_empty=False)
        )

        self.telegram_chatid = cast(
            str, self.get_config_option("chat_id", required=True, allow_empty=False)
        )

        self.timeout = cast(
            int, self.get_config_option("timeout", required_type="int", default=5)
        )

        self.support_catchup = True

    def send_telegram_notification(self, body: str) -> None:
        """Send a push notification."""

        response = requests.post(
            f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
            data={"chat_id": self.telegram_chatid, "text": body},
            timeout=self.timeout,
        )
        if not response.status_code == requests.codes.ok:
            raise RuntimeError("Unable to send telegram notification")

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Build up the content for the push notification."""

        alert_type = self.should_alert(monitor)
        if alert_type == AlertType.NONE:
            return

        body = self.build_message(AlertLength.FULL, alert_type, monitor)

        if not self._dry_run:
            try:
                self.send_telegram_notification(body)
            except Exception:
                self.alerter_logger.exception("Couldn't send push notification")
        else:
            self.alerter_logger.info("dry_run: would send push notification: %s", body)

    def _describe_action(self) -> str:
        return f"posting messages to {self.telegram_chatid} on Telegram"
