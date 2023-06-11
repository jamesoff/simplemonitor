"""
SimpleMonitor alerts via Twilio
"""

from typing import cast

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class TwilioSMSAlerter(Alerter):
    """Send SMS alerts using Twilio"""

    alerter_type = "twilio_sms"
    urgent = True

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        account_sid = cast(
            str, self.get_config_option("account_sid", required=True, allow_empty=False)
        )
        auth_token = cast(
            str, self.get_config_option("auth_token", required=True, allow_empty=False)
        )
        self.target = cast(
            str, self.get_config_option("target", required=True, allow_empty=False)
        )
        self.client = Client(account_sid, auth_token)

        self.sender = cast(str, self.get_config_option("sender", default="SmplMntr"))
        if not self.sender.startswith("+") and len(self.sender) > 11:
            self.alerter_logger.warning("truncating SMS sender name to 11 chars")
            self.sender = self.sender[:11]

        self.support_catchup = True

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Send an SMS alert."""

        alert_type = self.should_alert(monitor)
        if alert_type not in [AlertType.FAILURE, AlertType.SUCCESS]:
            return

        message = self.build_message(AlertLength.SMS, alert_type, monitor)

        params = {
            "body": message,
            "to": self.target,
            "from_": self.sender,
        }

        if not self._dry_run:
            try:
                self.client.messages.create(**params)
            except TwilioRestException:
                self.alerter_logger.exception("SMS sending failed")
        else:
            self.alerter_logger.info(
                "dry_run: would send SMS with Twilio: %s", str(params)
            )

    def _describe_action(self) -> str:
        return "SMSing {target} via Twilio".format(target=self.target)
