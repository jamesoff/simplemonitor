"""A collection of alerters for SimpleMonitor."""

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

    days = range(0,6)
    times_type = "always"
    time_info = [None, None]

    dry_run = False

    delay_notification = False
    ooh_failures = []
    # subclasses should set this to true if they support catchup notifications for delays
    support_catchup = False

    def __init__(self, config_options = {}):
        self.available = True
        if config_options.has_key("depend"):
            self.set_dependencies([x.strip() for x in config_options["depend"].split(",")])
        if config_options.has_key("limit"):
            self.limit = int(config_options["limit"])
        if config_options.has_key("times_type"):
            times_type = config_options["times_type"]
            if times_type == "always":
                pass
            elif times_type == "only":
                try:
                    time_info = [datetime.time(
                            int(config_options["time_lower"].split(":")[0]),
                            int(config_options["time_lower"].split(":")[1])),
                    
                            datetime.time(
                            int(config_options["time_upper"].split(":")[0]),
                            int(config_options["time_upper"].split(":")[1]))]
                except Exception, e:
                    print e
                    raise RuntimeError("error processing time limit definition")
                self.time_info = time_info
                self.times_type = "only"
            elif times_type == "not":
                try:
                    time_info = [datetime.time(
                            int(config_options["time_lower"].split(":")[0]),
                            int(config_options["time_lower"].split(":")[1])),
                    
                            datetime.time(
                            int(config_options["time_upper"].split(":")[0]),
                            int(config_options["time_upper"].split(":")[1]))]
                except:
                    raise RuntimeError("error processing time limit definition")
                self.time_info = time_info
                self.times_type = "not"
            else:
                raise RuntimeError("invalid times_type definition %s" % times_type)
        if config_options.has_key("days"):
            self.days = [int(x.strip()) for x in config_options["days"].split(",")]
        if config_options.has_key("delay"):
            if config_options["delay"] == "1":
                self.delay_notification = True
        if config_options.has_key("dry_run"):
            if config_options["dry_run"] == "1":
                self.dry_run = True

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
        out_of_hours = False

        if not self.available:
            return ""

        if not self.allowed_today():
            out_of_hours = True

        if not self.allowed_time():
            out_of_hours = True

        if monitor.virtual_fail_count() > 0:
            # Monitor has failed (not just first time)
            if self.delay_notification:
                if not out_of_hours:
                    if monitor.name in self.ooh_failures:
                        try:
                            self.ooh_failures.remove(monitor.name)
                        except:
                            print "Warning: Couldn't remove %s from OOH list; will maybe generate too many alerts."
                        if self.support_catchup:
                            return "catchup"
                        else:
                            return "failure"
            if monitor.virtual_fail_count() == self.limit:
                # This is the first time we've failed
                if out_of_hours:
                    if monitor.name not in self.ooh_failures:
                        self.ooh_failures.append(monitor.name)
                        return ""
                return "failure"
            return ""
            #TODO: fix the below to do access properly and not directly against the variable
        elif monitor.all_better_now() and monitor.last_error_count >= self.limit:
            try:
                self.ooh_failures.remove(monitor.name)
            except:
                pass
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

    def allowed_today(self):
        """Check if today is an allowed day for an alert."""
        if datetime.datetime.now().weekday() not in self.days:
            return False
        return True

    def allowed_time(self):
        """Check if now is an allowed time for an alert."""
        if self.times_type == "always":
            return True
        now = datetime.time(datetime.datetime.now().hour, datetime.datetime.now().minute, datetime.datetime.now().minute)
        if self.times_type == "only":
            if (now > self.time_info[0]) and (now < self.time_info[1]):
                return True
            else:
                return False
        elif self.times_type == "not":
            if (now > self.time_info[0]) and (now < self.time_info[1]):
                return False
            else:
                return True
        else:
            print "This should never happen! Unknown times_type in alerter."
            return True


class EMailAlerter(Alerter):
    """Send email alerts using SMTP to a mail server."""

    def __init__(self, config_options):
        Alerter.__init__(self, config_options)
        try:
            mail_host = config_options["host"]
            from_addr = config_options["from"]
            to_addr = config_options["to"]
        except:
            raise RuntimeError("Required configuration fields missing")

        if mail_host == "":
            raise RuntimeError("missing mailserver hostname")
        if from_addr == "":
            raise RuntimeError("missing mail from address")
        if to_addr == "":
            raise RuntimeError("missing mail to address")

        if config_options.has_key("port"):
            try:
                mail_port = int(config_options["port"])
            except:
                raise RuntimeError("mail port is not an integer")
        else:
            mail_port = 25

        self.mail_host = mail_host
        self.mail_port = mail_port
        self.from_addr = from_addr
        self.to_addr = to_addr

        self.support_catchup = True

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
        elif type == "catchup":
            message = "From: %s\r\nTo: %s\r\nSubject: [%s] Monitor %s failed earlier!" % (self.from_addr, self.to_addr, self.hostname, name)
            message = message + "\r\n\r\n"
            message = message + "Monitor %s on host %s failed earlier while this alerter was out of hours.\nFailed at: %s\nVirtual failure count: %d\nAdditional info: %s\nDescription: %s" % (name, self.hostname, monitor.first_failure_time().isoformat(), monitor.virtual_fail_count(), monitor.get_result(), monitor.describe())
        elif type == "success":
            message = "From: %s\r\nTo: %s\r\nSubject: [%s] Monitor %s succeeded" % (self.from_addr, self.to_addr, self.hostname, name)
            message = message + "\r\n\r\n"
            message = message + "Monitor %s on host %s is back up.\nOriginally failed at: %s\nDowntime: %d+%02d:%02d:%02d\nDescription: %s" % (name, self.hostname, monitor.first_failure_time().isoformat(), days, hours, minutes, seconds, monitor.describe())
        else:
            print "Unknown alert type %s" % type
            return

        if not self.dry_run:
            try:
                server = smtplib.SMTP(self.mail_host)
                server.sendmail(self.from_addr, self.to_addr, message)
                server.quit()
            except Exception, e:
                print "Couldn't send mail: %s", e
                self.available = False
        else:
            print "dry_run: would send email: %s" % message


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

        if config_options.has_key("sender"):
            sender = config_options["sender"]
            if len(sender) > 11:
                print "warning: truncating SMS sender name to 11 chars"
                sender = sender[:11]
        else:
            sender = "SmplMntr"

        self.username = username
        self.password = password
        self.target = target
        self.sender = urllib.quote(sender)

        self.support_catchup = True

    def send_alert(self, name, monitor):
        """Send an SMS alert."""

        type = self.should_alert(monitor)
        message = ""

        if not monitor.is_urgent():
            return

        (days, hours, minutes, seconds) = self.get_downtime(monitor)
        if type == "":
            return
        elif type == "catchup":
            (days, hours, minutes, seconds) = self.get_downtime(monitor)
            message = "[catchup] %s failed on %s at %s (%d+%02d:%02d:%02d)\n%s" % (name, self.hostname, monitor.first_failure_time().isoformat(), days, hours, minutes, seconds, monitor.get_result())
            message = urllib.quote_plus(message)
            url = "http://www.bulksms.co.uk:5567/eapi/submission/send_sms/2/2.0?username=%s&password=%s&message=%s&msisdn=%s&sender=%s" % (self.username, self.password, message, self.target, self.sender)
        elif type == "failure":
            (days, hours, minutes, seconds) = self.get_downtime(monitor)
            message = "%s failed on %s at %s (%d+%02d:%02d:%02d)\n%s" % (name, self.hostname, monitor.first_failure_time().isoformat(), days, hours, minutes, seconds, monitor.get_result())
            message = urllib.quote_plus(message)
            url = "http://www.bulksms.co.uk:5567/eapi/submission/send_sms/2/2.0?username=%s&password=%s&message=%s&msisdn=%s&sender=%s" % (self.username, self.password, message, self.target, self.sender)
        else:
            # we don't handle other types of message
            pass

        if message == "":
            return

        if not self.dry_run:
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
        else:
            print "dry_run: would send SMS: %s" % url
        return

