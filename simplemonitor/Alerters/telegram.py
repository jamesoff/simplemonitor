# coding=utf-8
from typing import cast

import requests

from ..Monitors.monitor import Monitor
from ..util import format_datetime
from .alerter import Alerter, register


@register
class TelegramAlerter(Alerter):
    """Send push notification via Telegram."""

    type = "telegram"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)

        self.telegram_token = cast(
            str, self.get_config_option("token", required=True, allow_empty=False)
        )

        self.telegram_chatid = cast(
            str, self.get_config_option("chat_id", required=True, allow_empty=False)
        )

        self.support_catchup = True

    def send_telegram_notification(self, body: str) -> None:
        """Send a push notification."""

        r = requests.post(
            "https://api.telegram.org/bot{}/sendMessage".format(self.telegram_token),
            data={"chat_id": self.telegram_chatid, "text": body},
        )
        if not r.status_code == requests.codes.ok:
            raise RuntimeError("Unable to send telegram notification")

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Build up the content for the push notification."""

        type = self.should_alert(monitor)
        (days, hours, minutes, seconds) = monitor.get_downtime()

        if monitor.is_remote():
            host = " on %s " % monitor.running_on
        else:
            host = " on host %s" % self.hostname

        body = ""

        if type == "":
            return
        elif type == "failure":
            body = """Monitor %s DOWN
Failed at: %s
Downtime: %d+%02d:%02d:%02d
Description: %s""" % (
                name,
                format_datetime(monitor.first_failure_time()),
                days,
                hours,
                minutes,
                seconds,
                monitor.describe(),
            )
            try:
                if monitor.recover_info != "":
                    body += "\nRecovery info: %s" % monitor.recover_info
            except AttributeError:
                body += "\nNo recovery info available"

        elif type == "success":
            body = """Monitor %s UP
Originally failed at: %s
Downtime: %d+%02d:%02d:%02d
Description: %s""" % (
                name,
                format_datetime(monitor.first_failure_time()),
                days,
                hours,
                minutes,
                seconds,
                monitor.describe(),
            )

        elif type == "catchup":
            body = (
                "Monitor %s%s failed earlier while this alerter was out of hours.\nFailed at: %s\nDescription: %s"
                % (
                    name,
                    host,
                    format_datetime(monitor.first_failure_time()),
                    monitor.describe(),
                )
            )

        else:
            self.alerter_logger.error("Unknown alert type %s", type)
            return

        if not self.dry_run:
            try:
                self.send_telegram_notification(body)
            except Exception:
                self.alerter_logger.exception("Couldn't send push notification")
                self.available = False
        else:
            self.alerter_logger.info("dry_run: would send push notification: %s" % body)
