import datetime
import smtplib
import urllib

from socket import gethostname

class Alerter:
    """Abstract class basis for alerters."""

    dependencies = []
    hostname = gethostname()
    available = False
    limit = 1

    def __init__(self, limit = 1):
        self.available = True
        self.limit = limit

    def set_dependencies(self, dependency_list):
        """Record which monitors we depend on.
        If a monitor we depend on fails, it means we can't reach the database, so we shouldn't bother trying to write to it."""

        self.dependencies = dependency_list

    def check_dependencies(self, failed_list):
        """Check if anything we depend on has failed."""
        for dependency in failed_list:
            if dependency in self.dependencies:
                self.available = False
                return False
        self.available = True

    def should_alert(self, monitor):
        """Check if we should bother alerting, and what type."""
        if not self.available:
            return ""

        if monitor.virtual_fail_count() > 0 and monitor.virtual_fail_count() == self.limit:
            return "failure"
            #TODO: fix the below to do access properly and not directly against the variable
        elif monitor.all_better_now() and monitor.last_error_count >= self.limit:
            return "success"
        else:
            return ""

    def send_alert(self, name, monitor):
        """Abstract function to do the alerting."""
        raise NotImplementedError

    def get_downtime(self, monitor):
        try:
            downtime = datetime.datetime.now() - monitor.first_failure_time()
            seconds = downtime.seconds
            if seconds > 3600:
                hours = seconds / 3600
                seconds = seconds - (hours * 3600)
            else:
                hours = 0
            if seconds > 60:
                minutes = seconds / 60
                seconds = seconds - (minutes * 60)
            else:
                minutes = 0
            return (downtime.days, hours, minutes, seconds)
        except:
            return (0,0,0,0)


class EMailAlerter(Alerter):
    """Send email alerts using SMTP to a mail server."""

    def __init__(self, mail_host, from_addr, to_addr, limit=1, mail_port=25):
        Alerter.__init__(self, limit)
        self.mail_host = mail_host
        self.mail_port = mail_port
        self.from_addr = from_addr
        self.to_addr = to_addr

    def send_alert(self, name, monitor):
        """Send the email."""

        type = self.should_alert(monitor)
        (days, hours, minutes, seconds) = self.get_downtime(monitor)
        
        if type == "":
            return
        elif type == "failure":
            message = "From: %s\r\nTo: %s\r\nSubject: [%s] Monitor %s failed!" % (self.from_addr, self.to_addr, self.hostname, name)
            message = message + "\r\n\r\n"
            message = message + "Monitor %s on host %s has failed.\nFailed at: %s\nVirtual failure count: %d\nAdditional info: %s\nDescription: %s" % (name, self.hostname, monitor.first_failure_time().isoformat(), monitor.virtual_fail_count(), monitor.get_result(), monitor.describe())
        elif type == "success":
            message = "From: %s\r\nTo: %s\r\nSubject: [%s] Monitor %s succeeded" % (self.from_addr, self.to_addr, self.hostname, name)
            message = message + "\r\n\r\n"
            message = message + "Monitor %s on host %s is back up.\nOriginally failed at: %s\nDowntime: %d+%02d:%02d:%02d\nDescription: %s" % (name, self.hostname, monitor.first_failure_time().isoformat(), days, hours, minutes, seconds, monitor.describe())
        else:
            print "Unknown alert type %s" % type
            return

        try:
            server = smtplib.SMTP(self.mail_host)
            server.sendmail(self.from_addr, self.to_addr, message)
            server.quit()
        except:
            print "Couldn't send mail"
            self.available = False


class BulkSMSAlerter(Alerter):
    """Send SMS alerts using the BulkSMS service.

    Subscription required, see http://www.bulksms.co.uk"""
    
    def __init__(self, username, password, target, sender, limit):
        Alerter.__init__(self, limit)
        self.username = username
        self.password = password
        self.target = target
        self.sender = urllib.quote(sender)

    def send_alert(self, name, monitor):
        """Send an SMS alert."""

        type = self.should_alert(monitor)

        if not monitor.is_urgent():
            return

        (days, hours, minutes, seconds) = self.get_downtime(monitor)
        if type == "":
            return
        elif type == "failure":
            (days, hours, minutes, seconds) = self.get_downtime(monitor)
            message = "%s failed on %s at %s (%d+%02d:%02d:%02d)\n%s" % (name, self.hostname, monitor.first_failure_time().isoformat(), days, hours, minutes, seconds, monitor.get_result())

            message = urllib.quote_plus(message)
            url = "http://www.bulksms.co.uk:5567/eapi/submission/send_sms/2/2.0?username=%s&password=%s&message=%s&msisdn=%s&sender=%s" % (self.username, self.password, message, self.target, self.sender)
            try:
                handle = urllib.urlopen(url)
                s = handle.read()
                if not s.startswith("0"):
                    print "Unable to send SMS: %s (%s)" % (s.split("|")[0], s.split("|")[1])
                    self.available = False
                handle.close()
            except:
                print "SMS sending failed"
                self.available = False
            return
        else:
            # we don't handle other types of message
            pass


