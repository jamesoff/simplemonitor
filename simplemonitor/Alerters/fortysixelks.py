try:
    import requests

    requests_available = True
except ImportError:
    requests_available = False

from typing import cast

from ..Monitors.monitor import Monitor
from ..util import AlerterConfigurationError
from .alerter import Alerter, AlertLength, AlertType, register


@register
class FortySixElksAlerter(Alerter):
    """Send SMS alerts using the 46elks SMS service.

    Account required, see https://www.46elks.com/"""

    alerter_type = "46elks"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        if not requests_available:
            self.alerter_logger.critical(
                "Requests package is not available, cannot use FortySixElksAlerter."
            )
            self.alerter_logger.critical("Try: pip install -r requirements.txt")
            return

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
        if self.sender[0] == "+" and self.sender[1:].isdigit():
            # sender is phone number
            pass
        elif len(self.sender) < 3:
            raise AlerterConfigurationError(
                "SMS sender name must be at least 3 chars long"
            )
        elif len(self.sender) > 11:
            self.alerter_logger.warning("truncating SMS sender name to 11 chars")
            self.sender = self.sender[:11]

        self.api_host = self.get_config_option("api_host", default="api.46elks.com")

        self.support_catchup = True

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Send an SMS alert."""

        if not monitor.urgent:
            return

        alert_type = self.should_alert(monitor)

        if alert_type not in [AlertType.CATCHUP, AlertType.FAILURE]:
            return

        message = self.build_message(AlertLength.SMS, alert_type, monitor)
        url = "https://{}/a1/SMS".format(self.api_host)
        auth = (self.username, self.password)
        params = {"from": self.sender, "to": self.target, "message": message}

        if not self._dry_run:
            try:
                response = requests.post(url, data=params, auth=auth)
                s = response.json()
                if s["status"] not in ("created", "delivered"):
                    self.alerter_logger.error("Unable to send SMS: %s", s)
                    self.available = False
            except Exception:
                self.alerter_logger.exception("SMS sending failed")
                self.available = False
        else:
            self.alerter_logger.info("dry_run: would send SMS: %s", url)
