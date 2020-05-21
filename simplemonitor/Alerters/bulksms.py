# coding=utf-8

from typing import cast

import requests

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class BulkSMSAlerter(Alerter):
    """Send SMS alerts using the BulkSMS service.

    Subscription required, see http://www.bulksms.co.uk"""

    alerter_type = "bulksms"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        self.username = cast(
            str, self.get_config_option("username", required=True, allow_empty=False)
        )
        self.password = cast(
            str, self.get_config_option("password", required=True, allow_empty=False)
        )
        self.target = cast(
            str, self.get_config_option("target", required=True, allow_empty=False)
        )

        self.sender = cast(str, self.get_config_option("sender", default="SmplMntr"))
        if len(self.sender) > 11:
            self.alerter_logger.warning("truncating SMS sender name to 11 chars")
            self.sender = self.sender[:11]

        self.api_host = self.get_config_option("api_host", default="www.bulksms.co.uk")

        self.support_catchup = True

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Send an SMS alert."""

        if not monitor.urgent:
            return

        alert_type = self.should_alert(monitor)
        if alert_type not in [AlertType.FAILURE, AlertType.SUCCESS]:
            return

        message = self.build_message(AlertLength.SMS, alert_type, monitor)

        url = "https://{}/eapi/submission/send_sms/2/2.0".format(self.api_host)
        params = {
            "username": self.username,
            "password": self.password,
            "message": message,
            "msisdn": self.target,
            "sender": self.sender,
            "repliable": "0",
        }

        if not self._dry_run:
            try:
                r = requests.get(url, params=params)
                s = r.text
                if not s.startswith("0"):
                    self.alerter_logger.error(
                        "Unable to send SMS: %s (%s)", s.split("|")[0], s.split("|")[1]
                    )
                    self.available = False
            except Exception:
                self.alerter_logger.exception("SMS sending failed")
                self.available = False
        else:
            self.alerter_logger.info(
                "dry_run: would send SMS: {} with message {}".format(url, message)
            )
