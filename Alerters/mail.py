import smtplib

from alerter import Alerter

class EMailAlerter(Alerter):
    """Send email alerts using MTP to a mail server."""

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

        #host = "on host %s" % self.hostname
        host = ""
        if monitor.is_remote():
            host = " on %s " % monitor.running_on
        
        if type == "":
            return
        elif type == "failure":
            message = "From: %s\r\nTo: %s\r\nSubject: [%s] Monitor %s failed!" % (self.from_addr, self.to_addr, self.hostname, name)
            message = message + "\r\n\r\n"
            try:
                message = message + """Monitor %s%s has failed.
                Failed at: %s\nDowntime: %d+%02d:%02d:%02d
                Virtual failure count: %d                
                Additional info: %s
                Description: %s""" % (
                        name, 
                        host, 
                        self.format_datetime(monitor.first_failure_time()), 
                        days, hours, minutes, seconds, 
                        monitor.virtual_fail_count(), 
                        monitor.get_result(), 
                        monitor.describe())
                if monitor.recover_info != "":
                    message += "\nRecovery info: %s" % monitor.recover_info
            except:
                message = message + "(unable to generate message!)"

        elif type == "success":
            message = "From: %s\r\nTo: %s\r\nSubject: [%s] Monitor %s succeeded" % (self.from_addr, self.to_addr, self.hostname, name)
            message = message + "\r\n\r\n"
            message = message + "Monitor %s%s is back up.\nOriginally failed at: %s\nDowntime: %d+%02d:%02d:%02d\nDescription: %s" % (name, host, self.format_datetime(monitor.first_failure_time()), days, hours, minutes, seconds, monitor.describe())

        elif type == "catchup":
            message = "From: %s\r\nTo: %s\r\nSubject: [%s] Monitor %s failed earlier!" % (self.from_addr, self.to_addr, self.hostname, name)
            message = message + "\r\n\r\n"
            message = message + "Monitor %s%s failed earlier while this alerter was out of hours.\nFailed at: %s\nVirtual failure count: %d\nAdditional info: %s\nDescription: %s" % (name, host, self.format_datetime(monitor.first_failure_time()), monitor.virtual_fail_count(), monitor.get_result(), monitor.describe())

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


