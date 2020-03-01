# coding=utf-8
from typing import cast

import requests

from ..Monitors.monitor import Monitor
from ..util import format_datetime
from .alerter import Alerter, AlertType, register


@register
class PushoverAlerter(Alerter):
    """Send push notification via Pushover."""

    _type = "pushover"

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
        downtime = monitor.get_downtime()

        if monitor.is_remote():
            host = " on %s " % monitor.running_on
        else:
            host = " on host %s" % self.hostname

        subject = ""
        body = ""

        if alert_type == AlertType.NONE:
            return
        elif alert_type == AlertType.FAILURE:
            subject = "[%s] Monitor %s Failed!" % (self.hostname, name)
            body = """Monitor %s%s has failed.\n
            Failed at: %s
            Downtime: %s
            Virtual failure count: %d
            Additional info: %s
            Description: %s""" % (
                name,
                host,
                format_datetime(monitor.first_failure_time()),
                downtime,
                monitor.virtual_fail_count(),
                monitor.get_result(),
                monitor.describe(),
            )
            try:
                if monitor.recover_info != "":
                    body += "\nRecovery info: %s" % monitor.recover_info
            except AttributeError:
                body += "\nNo recovery info available"

        elif alert_type == AlertType.SUCCESS:
            subject = "[%s] Monitor %s succeeded" % (self.hostname, name)
            body = (
                "Monitor %s%s is back up.\nOriginally failed at: %s\nDowntime: %s\nDescription: %s"
                % (
                    name,
                    host,
                    format_datetime(monitor.first_failure_time()),
                    downtime,
                    monitor.describe(),
                )
            )

        elif alert_type == AlertType.CATCHUP:
            subject = "[%s] Monitor %s failed earlier!" % (self.hostname, name)
            body = (
                "Monitor %s%s failed earlier while this alerter was out of hours.\nFailed at: %s\nVirtual failure count: %d\nAdditional info: %s\nDescription: %s"
                % (
                    name,
                    host,
                    format_datetime(monitor.first_failure_time()),
                    monitor.virtual_fail_count(),
                    monitor.get_result(),
                    monitor.describe(),
                )
            )

        else:
            self.alerter_logger.error("Unknown alert type %s", alert_type)
            return

        if not self._dry_run:
            try:
                self.send_pushover_notification(subject, body)
            except Exception:
                self.alerter_logger.exception("Couldn't send push notification")
                self.available = False
        else:
            self.alerter_logger.info("dry_run: would send push notification: %s", body)
