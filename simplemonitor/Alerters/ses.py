"""
SimpleMonitor alerts via Amazon Simple Email Service
"""

import os
from typing import Any, Dict, cast

import boto3
from botocore.exceptions import ClientError

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class SESAlerter(Alerter):
    """Send email alerts using Amazon's SES service."""

    alerter_type = "ses"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)

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

        alert_type = self.should_alert(monitor)

        mail = {}  # type: Dict[str, Any]
        mail["Source"] = self.from_addr
        mail["Destination"] = {"ToAddresses": [self.to_addr]}
        message = {}  # type: Dict[str, Any]

        if alert_type == AlertType.NONE:
            return

        message["Subject"] = {
            "Data": self.build_message(AlertLength.NOTIFICATION, alert_type, monitor)
        }
        message["Body"] = {
            "Text": {"Data": self.build_message(AlertLength.FULL, alert_type, monitor)}
        }

        mail["Message"] = message

        if not self._dry_run:
            try:
                client = boto3.client("ses", **self.ses_client_params)
                client.send_email(**mail)
            except ClientError:
                self.alerter_logger.exception("couldn't send mail")
        else:
            self.alerter_logger.info("dry_run: would send email:")
            self.alerter_logger.info("    Subject: %s", message["Subject"]["Data"])
            self.alerter_logger.info("    Body: %s", message["Body"]["Text"]["Data"])

    def _describe_action(self) -> str:
        return "emailing {target} via SES".format(target=self.to_addr)
