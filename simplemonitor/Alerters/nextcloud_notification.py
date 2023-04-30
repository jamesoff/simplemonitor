"""
SimpleMonitor alerts via Nextcloud Notifications
"""

from typing import cast

import requests

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class NextcloudNotificationAlerter(Alerter):
    alerter_type = "nextcloud_notification"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        self.nextcloud_token = cast(
            str, self.get_config_option("token", required=True, allow_empty=False)
        )
        self.nextcloud_user = cast(
            str, self.get_config_option("user", required=True, allow_empty=False)
        )
        self.nextcloud_server = cast(
            str, self.get_config_option("server", required=True, allow_empty=False)
        )
        self.nextcloud_receiver = cast(
            str, self.get_config_option("receiver", required=True, allow_empty=False)
        )
        self.timeout = cast(
            int, self.get_config_option("timeout", required_type="int", default=5)
        )

        self.support_catchup = True

    def send_nextcloud_notification(self, shortMessage: str, longMessage: str) -> None:
        uri = "ocs/v2.php/apps/notifications/api/v2/admin_notifications"
        requests.post(
            (
                f"https://{self.nextcloud_user}:{self.nextcloud_token}"
                f"@{self.nextcloud_server}/{uri}/{self.nextcloud_receiver}"
            ),
            headers={"OCS-APIREQUEST": "true"},
            data={
                "shortMessage": shortMessage,
                "longMessage": longMessage,
            },
            timeout=self.timeout,
        )

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Build up the content for the push notification."""

        alert_type = self.should_alert(monitor)

        if alert_type == AlertType.NONE:
            return
        short_message = self.build_message(
            AlertLength.NOTIFICATION, alert_type, monitor
        )
        long_message = self.build_message(AlertLength.FULL, alert_type, monitor)

        if not self._dry_run:
            try:
                self.send_nextcloud_notification(short_message, long_message)
            except Exception:
                self.alerter_logger.exception("Couldn't send push notification")
        else:
            self.alerter_logger.info(
                "dry_run: would send push notification: %s", long_message
            )

    def _describe_action(self) -> str:
        return "posting a Nextcloud Notification"
