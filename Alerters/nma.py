import urllib
import urllib2

from alerter import Alerter


class NMAAlerter(Alerter):
    """Send Push alerts using NMA service.

    Subscription required, see http://www.notifymyandroid.com/"""

    def __init__(self, config_options):
        Alerter.__init__(self, config_options)

        try:
            apikey = config_options["apikey"]
        except:
            raise RuntimeError("Required configuration fields missing")

        api_host = 'www.notifymyandroid.com'
        if 'api_host' in config_options:
            api_host = config_options['api_host']

        application = 'SimpleMonitor'
        if 'application' in config_options:
            application = config_options['application']

        self.apikey = apikey
        self.api_host = api_host
        self.application = application

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
                self.format_datetime(monitor.first_failure_time()),
                days, hours, minutes, seconds,
                monitor.get_result())
            url = "https://{}/publicapi/notify".format(self.api_host)
            params = urllib.urlencode({
                'apikey': self.apikey,
                'application': self.application,
                'description': message,
                'event': "%s: %s" % (name, monitor.get_result())
            })
        elif type == "failure":
            (days, hours, minutes, seconds) = self.get_downtime(monitor)
            message = "%s failed on %s at %s (%d+%02d:%02d:%02d)\n%s" % (
                name,
                monitor.running_on,
                self.format_datetime(monitor.first_failure_time()),
                days, hours, minutes, seconds,
                monitor.get_result())
            url = "https://{}/publicapi/notify".format(self.api_host)
            params = urllib.urlencode({
                'apikey': self.apikey,
                'application': self.application,
                'description': message,
                'event': "%s: %s" % (name, monitor.get_result())
            })
        else:
            # we don't handle other types of message
            pass

        if url == "":
            return

        if not self.dry_run:
            try:
                handle = urllib2.urlopen(url, params)
                s = handle.read()
                if not s.startswith('<?xml version="1.0" encoding="UTF-8"?><nma><success code="200"'):
                    print "Unable to send NMA: %s (%s)" % (s.split("|")[0], s.split("|")[1])
                    print "URL: %s, PARAMS: %s" % (url, params)
                    self.available = False
                handle.close()
            except Exception as e:
                print "NMA sending failed"
                print e
                print url
                print params
                self.available = False
        else:
            print "dry_run: would send NMA: %s" % url
        return
