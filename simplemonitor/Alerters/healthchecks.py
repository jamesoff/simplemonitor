"""
SimpleMonitor alerts via healthchecks
"""

from typing import cast

import json
import requests

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register
from ..util import check_group_match


@register
class HealthchecksAlerter(Alerter):
    """Send push notification via Healthchecks."""

    alerter_type = "healthchecks"
    headers = {"User-Agent": "SimpleMonitor"}

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        self.token = cast(
            str, self.get_config_option("token", required=True, allow_empty=False)
        )
        self.create = cast(str, self.get_config_option("create", required_type="bool"))
        hc_headers = cast(str, self.get_config_option("headers"))
        if hc_headers:
            try:
                self.headers = json.loads(hc_headers)
            except json.JSONDecodeError as e:
                self.alerter_logger.error(f"Parsing headers to JSON failed: {e}")

        self.timeout = cast(
            int, self.get_config_option("timeout", required_type="int", default=5)
        )

        self.support_catchup = True

    def send_notification(
        self,
        subject: str,
        body: str,
        alert_type: str,
        name: str,
        slug: str,
        dry_run=False,
    ) -> None:
        """Send a push notification."""
        url = "https://hc-ping.com/" + self.token + "/" + slug
        if alert_type != "success":
            url += "/fail"
        if self.create:
            url += "?create=1"
        if dry_run:
            self.alerter_logger.info(
                f"dry_run - monitor: {self.name} | alerter: {name} | {url}"
            )
            return

        data = ""
        data_json = {}
        if subject:
            data_json["subject"] = subject
        if body:
            data = body
            data_json["body"] = body.strip()

        try:
            req = requests.post(
                url,
                data=data,
                # json=data_json,
                headers=self.headers,
                timeout=self.timeout,
            )
            req.raise_for_status()
            self.alerter_logger.info(f"monitor: {name} | alerter: {self.name} | {url}")
        except requests.exceptions.RequestException:
            raise ValueError(
                f"alerter: {self.name} | {slug} | {req.status_code}"
            ) from None

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Build up the content for the push notification."""

        if monitor.slug is None or not monitor.enabled:
            return

        if not check_group_match(monitor.group, self.groups):
            return

        alert_type = self.should_alert(monitor)

        if alert_type == AlertType.NONE:
            if monitor.failures:
                alert_type = AlertType.CATCHUP
            else:
                alert_type = AlertType.SUCCESS

        subject = self.build_message(AlertLength.NOTIFICATION, alert_type, monitor)
        body = self.build_message(AlertLength.FULL, alert_type, monitor)

        if not self._dry_run:
            try:
                self.send_notification(
                    subject, body, alert_type.value, monitor.name, monitor.slug
                )
            except Exception as e:
                self.alerter_logger.error(
                    f"Notification failed: monitor: {monitor.name} | group: {monitor.group} | {e}"
                )
        else:
            self.send_notification(
                subject,
                body,
                alert_type.value,
                monitor.name,
                monitor.slug,
                dry_run=self._dry_run,
            )

    def _describe_action(self) -> str:
        return "posting to healthchecks"
