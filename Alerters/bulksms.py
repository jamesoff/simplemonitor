import urllib

from alerter import Alerter


class BulkSMSAlerter(Alerter):
    """Send SMS alerts using the BulkSMS service.

    Subscription required, see http://www.bulksms.co.uk"""

    def __init__(self, config_options):
        Alerter.__init__(self, config_options)

        try:
            username = config_options["username"]
            password = config_options["password"]
            target = config_options["target"]
        except:
            raise RuntimeError("Required configuration fields missing")

        if 'sender' in config_options:
            sender = config_options["sender"]
            if len(sender) > 11:
                print "warning: truncating SMS sender name to 11 chars"
                sender = sender[:11]
        else:
            sender = "SmplMntr"

        self.username = username
        self.password = password
        self.target = target
        self.sender = sender

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
                print "Warning! Truncating SMS message to 160 chars."
                message = message[:156] + "..."
            url = "https://bulksms.vsms.net/eapi/submission/send_sms/2/2.0"
            params = urllib.urlencode({'username' : self.username, 'password' : self.password, 'message' : message, 'msisdn' : self.target, 'sender' : self.sender, 'repliable' : '0'})
        elif type == "failure":
            (days, hours, minutes, seconds) = self.get_downtime(monitor)
            message = "%s failed on %s at %s (%d+%02d:%02d:%02d)\n%s" % (
                name,
                monitor.running_on,
                self.format_datetime(monitor.first_failure_time()),
                days, hours, minutes, seconds,
                monitor.get_result())
            if len(message) > 160:
                print "Warning! Truncating SMS message to 160 chars."
                message = message[:156] + "..."
            url = "https://bulksms.vsms.net/eapi/submission/send_sms/2/2.0"
            params = urllib.urlencode({'username' : self.username, 'password' : self.password, 'message' : message, 'msisdn' : self.target, 'sender' : self.sender, 'repliable' : '0'})
        else:
            # we don't handle other types of message
            pass

        if url == "":
            return

        if not self.dry_run:
            try:
                handle = urllib.urlopen(url, params)
                s = handle.read()
                if not s.startswith("0"):
                    print "Unable to send SMS: %s (%s)" % (s.split("|")[0], s.split("|")[1])
                    print "URL: %s, PARAMS: %s" % (url, params)
                    self.available = False
                handle.close()
            except:
                print "SMS sending failed"
                self.available = False
        else:
            print "dry_run: would send SMS: %s" % url
        return
