"""
SimpleMonitor alerts via SMS77
"""

from typing import cast

import requests

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class SMS77Alerter(Alerter):
    """Send SMS alerts using the sms77 service"""

    alerter_type = "sms77"
    urgent = True

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        self.api_key = cast(
            str, self.get_config_option("api_key", required=True, allow_empty=False)
        )
        self.target = cast(
            str, self.get_config_option("target", required=True, allow_empty=False)
        )

        self.sender = cast(str, self.get_config_option("sender", default="SmplMntr"))
        if len(self.sender) > 11:
            self.alerter_logger.warning("truncating SMS sender name to 11 chars")
            self.sender = self.sender[:11]

        self.timeout = cast(
            int, self.get_config_option("timeout", required_type="int", default=5)
        )

        self.support_catchup = True

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Send an SMS alert"""

        alert_type = self.should_alert(monitor)
        if alert_type not in [AlertType.FAILURE, AlertType.SUCCESS]:
            return

        message = self.build_message(AlertLength.SMS, alert_type, monitor)

        url = "https://gateway.sms77.io/api/sms"
        params = {
            "text": message,
            "to": self.target,
            "from": self.sender,
            "p": self.api_key,
        }

        if not self._dry_run:
            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                status = response.text
                if not status.startswith("100"):
                    self.alerter_logger.error(
                        "Unable to send SMS: status code %s", status
                    )
            except requests.RequestException:
                self.alerter_logger.exception("SMS sending failed")
        else:
            self.alerter_logger.info("dry_run: would send SMS: %s", message)

    def _describe_action(self) -> str:
        return "SMSing {target} via SMS77".format(target=self.target)
