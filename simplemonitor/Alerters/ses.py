# coding=utf-8
try:
    import boto3

    boto3_available = True
except ImportError:
    boto3_available = False

import os
from typing import Any, Dict, cast

from ..Monitors.monitor import Monitor
from ..util import format_datetime
from .alerter import Alerter, register


@register
class SESAlerter(Alerter):
    """Send email alerts using Amazon's SES service."""

    type = "ses"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        if not boto3_available:
            self.alerter_logger.critical(
                "boto3 package is not available, cannot use SESAlerter."
            )
            self.available = False
            return

        self.from_addr = cast(str, self.get_config_option("from", allow_empty=False))
        self.to_addr = cast(str, self.get_config_option("to", allow_empty=False))

        self.support_catchup = True

        self.ses_client_params = {}  # type: Dict[str, str]

        aws_region = cast(str, self.get_config_option("aws_region"))
        if aws_region:
            os.environ["AWS_DEFAULT_REGION"] = aws_region

        aws_access_key = cast(str, self.get_config_option("aws_access_key"))
        aws_secret_key = cast(str, self.get_config_option("aws_secret_access_key"))

        if aws_access_key and aws_secret_key:
            self.ses_client_params["aws_access_key_id"] = aws_access_key
            self.ses_client_params["aws_secret_access_key"] = aws_secret_key

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Send the email."""

        type = self.should_alert(monitor)
        (days, hours, minutes, seconds) = monitor.get_downtime()

        if monitor.is_remote():
            host = " on %s " % monitor.running_on
        else:
            host = " on host %s" % self.hostname

        mail = {}  # type: Dict[str, Any]
        mail["Source"] = self.from_addr
        mail["Destination"] = {"ToAddresses": [self.to_addr]}

        if type == "":
            return
        elif type == "failure":
            message = {}  # type: Dict[str, Any]
            message["Subject"] = {
                "Data": "[%s] Monitor %s Failed!" % (self.hostname, name)
            }
            message["Body"] = {
                "Text": {
                    "Data": """Monitor %s%s has failed.
            Failed at: %s
            Downtime: %d+%02d:%02d:%02d
            Virtual failure count: %d
            Additional info: %s
            Description: %s"""
                    % (
                        name,
                        host,
                        format_datetime(monitor.first_failure_time()),
                        days,
                        hours,
                        minutes,
                        seconds,
                        monitor.virtual_fail_count(),
                        monitor.get_result(),
                        monitor.describe(),
                    )
                }
            }
            try:
                if monitor.recover_info != "":
                    message["Body"]["Text"]["Data"] += (
                        "\nRecovery info: %s" % monitor.recover_info
                    )
            except AttributeError:
                message["Body"]["Text"]["Data"] += "\nNo recovery info available"

        elif type == "success":
            message = {
                "Subject": {"Data": "[%s] Monitor %s succeeded" % (self.hostname, name)}
            }
            message["Body"] = {
                "Text": {
                    "Data": "Monitor %s%s is back up.\nOriginally failed at: %s\nDowntime: %d+%02d:%02d:%02d\nDescription: %s"
                    % (
                        name,
                        host,
                        format_datetime(monitor.first_failure_time()),
                        days,
                        hours,
                        minutes,
                        seconds,
                        monitor.describe(),
                    )
                }
            }

        elif type == "catchup":
            message = {
                "Subject": {
                    "Data": "[%s] Monitor %s failed earlier!" % (self.hostname, name)
                }
            }
            message["Body"] = {
                "Text": {
                    "Data": "Monitor %s%s failed earlier while this alerter was out of hours.\nFailed at: %s\nVirtual failure count: %d\nAdditional info: %s\nDescription: %s"
                    % (
                        name,
                        host,
                        format_datetime(monitor.first_failure_time()),
                        monitor.virtual_fail_count(),
                        monitor.get_result(),
                        monitor.describe(),
                    )
                }
            }

        else:
            self.alerter_logger.critical("Unknown alert type %s", type)
            return

        mail["Message"] = message

        if not self.dry_run:
            try:
                client = boto3.client("ses", **self.ses_client_params)
                client.send_email(**mail)
            except Exception:
                self.alerter_logger.exception("couldn't send mail")
                self.available = False
        else:
            self.alerter_logger.info("dry_run: would send email:")
            self.alerter_logger.info("    Subject: %s", message["Subject"]["Data"])
            self.alerter_logger.info("    Body: %s", message["Body"]["Text"]["Data"])
