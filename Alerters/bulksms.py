# coding=utf-8

import requests

from util import format_datetime
from .alerter import Alerter


class BulkSMSAlerter(Alerter):
    """Send SMS alerts using the BulkSMS service.

    Subscription required, see http://www.bulksms.co.uk"""

    def __init__(self, config_options):
        Alerter.__init__(self, config_options)
        self.username = Alerter.get_config_option(
            config_options,
            'username',
            required=True,
            allow_empty=False
        )
        self.password = Alerter.get_config_option(
            config_options,
            'password',
            required=True,
            allow_empty=False
        )
        self.target = Alerter.get_config_option(
            config_options,
            'target',
            required=True,
            allow_empty=False
        )

        self.sender = Alerter.get_config_option(
            config_options,
            'sender',
            default='SmplMntr'
        )
        if len(self.sender) > 11:
            self.alerter_logger.warning("truncating SMS sender name to 11 chars")
            self.sender = self.sender[:11]

        self.api_host = Alerter.get_config_option(
            config_options,
            'api_host',
            default='www.bulksms.co.uk'
        )

        self.support_catchup = True

    def send_alert(self, name, monitor):
        """Send an SMS alert."""

        if not monitor.is_urgent():
            return

        type_ = self.should_alert(monitor)
        message = ""
        url = ""

        (days, hours, minutes, seconds) = self.get_downtime(monitor)
        if type_ == "":
            return
        elif type_ == "catchup":
            (days, hours, minutes, seconds) = self.get_downtime(monitor)
            message = "catchup: %s failed on %s at %s (%d+%02d:%02d:%02d)\n%s" % (
                name,
                monitor.running_on,
                format_datetime(monitor.first_failure_time()),
                days, hours, minutes, seconds,
                monitor.get_result())
            if len(message) > 160:
                self.alerter_logger.warning("Truncating SMS message to 160 chars.")
                message = message[:156] + "..."
            url = "https://{}/eapi/submission/send_sms/2/2.0".format(self.api_host)
            params = {
                'username': self.username,
                'password': self.password,
                'message': message,
                'msisdn': self.target,
                'sender': self.sender,
                'repliable': '0'
            }
        elif type_ == "failure":
            (days, hours, minutes, seconds) = self.get_downtime(monitor)
            message = "%s failed on %s at %s (%d+%02d:%02d:%02d)\n%s" % (
                name,
                monitor.running_on,
                format_datetime(monitor.first_failure_time()),
                days, hours, minutes, seconds,
                monitor.get_result())
            if len(message) > 160:
                self.alerter_logger.warning("Truncating SMS message to 160 chars.")
                message = message[:156] + "..."
            url = "https://{}/eapi/submission/send_sms/2/2.0".format(self.api_host)
            params = {
                'username': self.username,
                'password': self.password,
                'message': message,
                'msisdn': self.target,
                'sender': self.sender,
                'repliable': '0'
            }
        else:
            # we don't handle other types of message
            pass

        if url == "":
            return

        if not self.dry_run:
            try:
                r = requests.get(url, params=params)
                s = r.text
                if not s.startswith("0"):
                    self.alerter_logger.error("Unable to send SMS: %s (%s)", s.split("|")[0], s.split("|")[1])
                    self.available = False
            except Exception as e:
                self.alerter_logger.exception("SMS sending failed")
                self.available = False
        else:
            self.alerter_logger.info("dry_run: would send SMS: %s", url)
        return
