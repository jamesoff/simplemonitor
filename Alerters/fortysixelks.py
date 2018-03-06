try:
    import requests
    requests_available = True
except:
    requests_available = False

from .alerter import Alerter


class FortySixElksAlerter(Alerter):
    """Send SMS alerts using the 46elks SMS service.

    Account required, see https://www.46elks.com/"""

    def __init__(self, config_options):
        if not requests_available:
            print("Requests package is not available, cannot use FortySixElksAlerter.")
            print("Try: pip install -r requirements.txt")
            return

        Alerter.__init__(self, config_options)

        try:
            username = config_options["username"]
            password = config_options["password"]
            target = config_options["target"]
        except:
            raise RuntimeError("Required configuration fields missing")

        if 'sender' in config_options:
            sender = config_options["sender"]
            if sender[0] == '+' and sender[1:].isdigit():
                # sender is phone number
                pass
            elif len(sender) < 3:
                raise RuntimeError("SMS sender name must be at least 3 chars long")
            elif len(sender) > 11:
                print("warning: truncating SMS sender name to 11 chars")
                sender = sender[:11]
        else:
            sender = "SmplMntr"

        api_host = 'api.46elks.com'
        if 'api_host' in config_options:
            api_host = config_options['api_host']

        self.username = username
        self.password = password
        self.target = target
        self.sender = sender
        self.api_host = api_host

        self.support_catchup = True

    def send_alert(self, name, monitor):
        """Send an SMS alert."""

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
                self.format_datetime(monitor.first_failure_time()),
                days, hours, minutes, seconds,
                monitor.get_result())
            if len(message) > 160:
                print("Warning! Truncating SMS message to 160 chars.")
                message = message[:156] + "..."
            url = "https://{}/a1/SMS".format(self.api_host)
            auth = (self.username, self.password)
            params = {
                'from': self.sender,
                'to': self.target,
                'message': message,
            }
        elif type == "failure":
            (days, hours, minutes, seconds) = self.get_downtime(monitor)
            message = "%s failed on %s at %s (%d+%02d:%02d:%02d)\n%s" % (
                name,
                monitor.running_on,
                self.format_datetime(monitor.first_failure_time()),
                days, hours, minutes, seconds,
                monitor.get_result())
            if len(message) > 160:
                print("Warning! Truncating SMS message to 160 chars.")
                message = message[:156] + "..."
            url = "https://{}/a1/SMS".format(self.api_host)
            auth = (self.username, self.password)
            params = {
                'from': self.sender,
                'to': self.target,
                'message': message,
            }
        else:
            # we don't handle other types of message
            pass

        if url == "":
            return

        if not self.dry_run:
            try:
                response = requests.post(url, data=params, auth=auth)
                s = response.json()
                if s['status'] not in ('created', 'delivered'):
                    print("Unable to send SMS: %s" % s)
                    print("URL: %s, PARAMS: %s" % (url, params))
                    self.available = False
            except Exception as e:
                print("SMS sending failed")
                print(e)
                print(url)
                print(params)
                self.available = False
        else:
            print("dry_run: would send SMS: %s" % url)
        return
