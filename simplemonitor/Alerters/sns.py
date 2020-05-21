# coding=utf-8
try:
    import boto3

    boto3_available = True
except ImportError:
    boto3_available = False

from typing import Dict, Optional, cast

from ..Monitors.monitor import Monitor
from ..util import AlerterConfigurationError
from .alerter import Alerter, AlertLength, AlertType, register


@register
class SNSAlerter(Alerter):
    """Send notifications using Amazon SNS"""

    alerter_type = "sns"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        if not boto3_available:
            self.alerter_logger.critical(
                "boto3 package is not available, cannot use SNSAlerter."
            )
            self.available = False
            return

        self.topic = cast(str, self.get_config_option("topic", default=""))
        self.number = cast(str, self.get_config_option("number", default=""))

        if not self.topic and not self.number:
            raise AlerterConfigurationError("need one of topic or number to be set")

        if self.topic and self.number:
            raise AlerterConfigurationError("cannot set both topic and number")

        self.support_catchup = True

        self.sns_client_params = {}  # type: Dict[str, str]

        aws_region = cast(str, self.get_config_option("aws_region", default=""))
        if aws_region:
            self.sns_client_params["region_name"] = aws_region

        aws_access_key = cast(str, self.get_config_option("aws_access_key", default=""))
        aws_secret_key = cast(
            str, self.get_config_option("aws_secret_access_key", default="")
        )

        if aws_access_key and aws_secret_key:
            self.sns_client_params["aws_access_key_id"] = aws_access_key
            self.sns_client_params["aws_secret_access_key"] = aws_secret_key

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Send the email."""

        if not monitor.urgent:
            return

        alert_type = self.should_alert(monitor)

        if alert_type == AlertType.NONE:
            return

        subject = None  # type: Optional[str]
        if self.topic:
            subject = self.build_message(AlertLength.NOTIFICATION, alert_type, monitor)
            message = self.build_message(AlertLength.FULL, alert_type, monitor)
        elif self.number:
            message = self.build_message(AlertLength.SMS, alert_type, monitor)

        if not self._dry_run:
            try:
                client = boto3.client("sns", **self.sns_client_params)
                if subject is None:
                    client.publish(PhoneNumber=self.number, Message=message)
                else:
                    client.publish(
                        TopicArn=self.topic, Subject=subject, Message=message
                    )
            except Exception:
                self.alerter_logger.exception("couldn't send notification")
                self.available = False
        else:
            if subject is None:
                target = self.number
            else:
                target = self.topic
            self.alerter_logger.info("dry_run: would send notifiction to %s:", target)
            if subject is not None:
                self.alerter_logger.info("    Subject: %s", subject)
            self.alerter_logger.info("    Message: %s", message)
