# coding=utf-8
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, cast

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class EMailAlerter(Alerter):
    """Send email alerts using SMTP to a mail server."""

    _type = "email"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        self.mail_host = cast(
            str, self.get_config_option("host", required=True, allow_empty=False)
        )
        self.from_addr = cast(
            str, self.get_config_option("from", required=True, allow_empty=False)
        )
        self.to_addr = cast(
            str, self.get_config_option("to", required=True, allow_empty=False)
        )
        self.mail_port = cast(
            int, self.get_config_option("port", required_type="int", default=25)
        )
        self.username = cast(str, self.get_config_option("username"))
        self.password = cast(str, self.get_config_option("password"))
        self.ssl = cast(
            Optional[str],
            self.get_config_option("ssl", allowed_values=["starttls", "yes", None]),
        )
        if self.ssl == "yes":
            self.alerter_logger.warning("ssl=yes for email alerter is untested")

        self.support_catchup = True

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Send the email."""

        alert_type = self.should_alert(monitor)

        message = MIMEMultipart()
        message["From"] = self.from_addr
        message["To"] = self.to_addr

        if alert_type == AlertType.NONE:
            return
        message["Subject"] = self.build_message(
            AlertLength.NOTIFICATION, alert_type, monitor
        )
        body = self.build_message(AlertLength.FULL, alert_type, monitor)
        message.attach(MIMEText(body, "plain"))

        if not self._dry_run:
            try:
                if self.ssl is None or self.ssl == "starttls":
                    server = smtplib.SMTP(self.mail_host, self.mail_port)
                elif self.ssl == "yes":
                    server = smtplib.SMTP_SSL(self.mail_host, self.mail_port)

                if self.ssl == "starttls":
                    server.starttls()

                if self.username is not None:
                    server.login(self.username, self.password)
                server.sendmail(
                    self.from_addr, self.to_addr.split(";"), message.as_string()
                )
                server.quit()
            except Exception:
                self.alerter_logger.exception("couldn't send mail")
                self.available = False
        else:
            self.alerter_logger.info(
                "dry_run: would send email: %s", message.as_string()
            )
