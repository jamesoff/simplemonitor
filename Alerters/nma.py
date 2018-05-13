import requests

from util import format_datetime
from .alerter import Alerter


class NMAAlerter(Alerter):
    """Send Push alerts using NMA service.

    Subscription required, see http://www.notifymyandroid.com/"""

    def __init__(self, config_options):
        Alerter.__init__(self, config_options)

        self.apikey = Alerter.get_config_option(
            config_options,
            'apikey',
            required=True,
            allow_empty=False
        )
        self.api_host = Alerter.get_config_option(
            config_options,
            'api_host',
            default='www.notifymyandroid.com'
        )
        self.application = Alerter.get_config_option(
            config_options,
            'application',
            default='SimpleMonitor'
        )

        self.support_catchup = True

    def send_alert(self, name, monitor):
        """Send an alert."""

        if not monitor.is_urgent():
            return

        type = self.should_alert(monitor)
        message = ""
        url = ""

        (days, hours, minutes, seconds) = self.get_downtime(monitor)
        if type == "":
            return
        elif type == "catchup":
            (days, hours, minutes, seconds) = self.get_downtime(monitor)
            message = "catchup: %s failed on %s at %s (%d+%02d:%02d:%02d)\n%s" % (
                name,
                monitor.running_on,
                format_datetime(monitor.first_failure_time()),
                days, hours, minutes, seconds,
                monitor.get_result())
            url = "https://{}/publicapi/notify".format(self.api_host)
            params = {
                'apikey': self.apikey,
                'application': self.application,
                'description': message,
                'event': "%s: %s" % (name, monitor.get_result())
            }
        elif type == "failure":
            (days, hours, minutes, seconds) = self.get_downtime(monitor)
            message = "%s failed on %s at %s (%d+%02d:%02d:%02d)\n%s" % (
                name,
                monitor.running_on,
                format_datetime(monitor.first_failure_time()),
                days, hours, minutes, seconds,
                monitor.get_result())
            url = "https://{}/publicapi/notify".format(self.api_host)
            params = {
                'apikey': self.apikey,
                'application': self.application,
                'description': message,
                'event': "%s: %s" % (name, monitor.get_result())
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
                if not s.startswith('<?xml version="1.0" encoding="UTF-8"?><nma><success code="200"'):
                    self.alerter_logger.error("Unable to send NMA: %s (%s)", s.split("|")[0], s.split("|")[1])
                    self.alerter_logger.error("URL: %s, PARAMS: %s", url, params)
                    self.available = False
            except Exception as e:
                self.alerter_logger.exception("NMA sending failed")
                self.available = False
        else:
            self.alerter_logger.info("dry_run: would send NMA: %s", url)
        return
