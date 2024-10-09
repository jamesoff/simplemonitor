"""
SimpleMonitor alerts via healthchecks
"""

from typing import cast

import json
import requests

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class HealthchecksAlerter(Alerter):
    """Send push notification via Healthchecks."""

    alerter_type = "healthchecks"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        self.hc_token = cast(
            str, self.get_config_option("token", required=True, allow_empty=False)
        )
        self.hc_create = cast(
            str, self.get_config_option("create", required_type=bool)
        )
        hc_headers = cast(
            str, self.get_config_option("headers")
        )
        if hc_headers:
            try:
                self.hc_headers = json.loads(hc_headers)
            except:
                self.hc_headers = None
        self.timeout = cast(
            int, self.get_config_option("timeout", required_type="int", default=5)
        )

        self.support_catchup = True

    def send_hc_notification(self, subject: str, body: str, alert_type: str, name: str, slug: str, dry_run=False) -> None:
        """Send a push notification."""
        url = "https://hc-ping.com/" + self.hc_token + "/" + slug
        if alert_type != "success":
            url += "/fail"
        if self.hc_create:
            url += "?create=1"
        if dry_run:
            self.alerter_logger.info("dry_run - url: %s", url)
            return
        req = requests.post(
            url,
            data=body,
            headers=self.hc_headers,
            timeout=self.timeout,
        )
        req.raise_for_status()
        self.alerter_logger.info("monitor: %s - pushing to url: %s", name, url)

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Build up the content for the push notification."""

        alert_type = self.should_alert(monitor)

        if monitor.slug is None or not monitor.enabled:
            return

        if alert_type == AlertType.NONE:
            if monitor.failures:
                alert_type = AlertType.CATCHUP
            else:
                alert_type = AlertType.SUCCESS

        subject = self.build_message(AlertLength.NOTIFICATION, alert_type, monitor)
        body = self.build_message(AlertLength.FULL, alert_type, monitor)

        if not self._dry_run:
            try:
                self.send_hc_notification(subject, body, alert_type.value, monitor.name, monitor.slug)
            except Exception:
                self.alerter_logger.exception("Couldn't send push notification")
        else:
            self.send_hc_notification(subject, body, alert_type.value, monitor.name, monitor.slug, dry_run=self._dry_run)

    def _describe_action(self) -> str:
        return "posting to healthchecks"
