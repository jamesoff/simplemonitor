import requests

from util import format_datetime
from .alerter import Alerter


class PushbulletAlerter(Alerter):
    """Send push notification via Pushbullet."""

    def __init__(self, config_options):
        Alerter.__init__(self, config_options)

        self.pushbullet_token = Alerter.get_config_option(
            config_options,
            'token',
            required=True,
            allow_empty=False
        )

        self.support_catchup = True

    def send_pushbullet_notification(self, subject, body):
        """Send a push notification."""

        _payload = {'type': 'note', 'title': subject, 'body': body}
        _auth = requests.auth.HTTPBasicAuth(self.pushbullet_token, '')

        r = requests.post('https://api.pushbullet.com/v2/pushes', data=_payload, auth=_auth)
        if not r.status_code == requests.codes.ok:
            raise RuntimeError("Unable to send Pushbullet notification")

    def send_alert(self, name, monitor):
        """Build up the content for the push notification."""

        type = self.should_alert(monitor)
        (days, hours, minutes, seconds) = monitor.get_downtime()

        if monitor.is_remote():
            host = " on %s " % monitor.running_on
        else:
            host = " on host %s" % self.hostname

        subject = ""
        body = ""

        if type == "":
            return
        elif type == "failure":
            subject = "[%s] Monitor %s Failed!" % (self.hostname, name)
            body = """Monitor %s%s has failed.\n
            Failed at: %s
            Downtime: %d+%02d:%02d:%02d
            Virtual failure count: %d
            Additional info: %s
            Description: %s""" % (
                name,
                host,
                format_datetime(monitor.first_failure_time()),
                days, hours, minutes, seconds,
                monitor.virtual_fail_count(),
                monitor.get_result(),
                monitor.describe())
            try:
                if monitor.recover_info != "":
                    body += "\nRecovery info: %s" % monitor.recover_info
            except AttributeError:
                body += "\nNo recovery info available"

        elif type == "success":
            subject = "[%s] Monitor %s succeeded" % (self.hostname, name)
            body = "Monitor %s%s is back up.\nOriginally failed at: %s\nDowntime: %d+%02d:%02d:%02d\nDescription: %s" % (
                name, host, format_datetime(monitor.first_failure_time()), days, hours, minutes, seconds,
                monitor.describe())

        elif type == "catchup":
            subject = "[%s] Monitor %s failed earlier!" % (self.hostname, name)
            body = "Monitor %s%s failed earlier while this alerter was out of hours.\nFailed at: %s\nVirtual failure count: %d\nAdditional info: %s\nDescription: %s" % (
                name, host, format_datetime(monitor.first_failure_time()), monitor.virtual_fail_count(),
                monitor.get_result(), monitor.describe())

        else:
            self.alerter_logger.error("Unknown alert type %s", type)
            return

        if not self.dry_run:
            try:
                self.send_pushbullet_notification(subject, body)
            except Exception as e:
                self.alerter_logger.exception("Couldn't send push notification")
                self.available = False
        else:
            self.alerter_logger.info("dry_run: would send push notification: %s" % body)
