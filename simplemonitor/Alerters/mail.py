"""
SimpleMonitor alerts via email/SMTP
"""

import email.utils
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, cast

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class EMailAlerter(Alerter):
    """Send email alerts using SMTP to a mail server"""

    alerter_type = "email"

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
        self.cc_addr = cast(Optional[str], self.get_config_option("cc", required=False))
        self.mail_port = cast(
            int, self.get_config_option("port", required_type="int", default=25)
        )
        self.username = cast(str, self.get_config_option("username"))
        self.password = cast(str, self.get_config_option("password"))
        self.ssl = cast(
            Optional[str],
            self.get_config_option("ssl", allowed_values=["starttls", "yes", None]),
        )

        self.support_catchup = True

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Send the email"""

        alert_type = self.should_alert(monitor)
        if alert_type == AlertType.NONE:
            return

        message = MIMEMultipart()
        message["From"] = self.from_addr
        message["To"] = self.to_addr.replace(";", ",")
        message["Date"] = email.utils.formatdate()
        envelope_to = self.to_addr.split(";")
        if self.cc_addr:
            message["CC"] = self.cc_addr.replace(";", ",")
            envelope_to.extend(self.cc_addr.split(";"))

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
                else:
                    self.alerter_logger.critical(
                        "Cannot send mail, alerter's ssl configuration is broken"
                    )
                    return

                if self.ssl == "starttls":
                    server.starttls()

                if self.username is not None:
                    try:
                        server.login(self.username, self.password)
                    except smtplib.SMTPNotSupportedError:
                        self.alerter_logger.exception(
                            "You may need to add ssl=starttls and/or port=587 to "
                            "your alerter config"
                        )
                        return
                server.sendmail(self.from_addr, envelope_to, message.as_string())
                server.quit()
            except smtplib.SMTPException:
                self.alerter_logger.exception("couldn't send mail")
        else:
            self.alerter_logger.info(
                "dry_run: would send email: %s", message.as_string()
            )

    def _describe_action(self) -> str:
        return "sending mail to {target}".format(target=self.to_addr)
