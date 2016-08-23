import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

from alerter import Alerter


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

        if 'port' in config_options:
            try:
                mail_port = int(config_options["port"])
            except:
                raise RuntimeError("mail port is not an integer")
        else:
            mail_port = 25

        self.username = None
        self.password = None
        if 'username' in config_options:
            self.username = config_options['username']
        if 'password' in config_options:
            self.password = config_options['password']

        if 'ssl' in config_options:
            if config_options['ssl'] == 'starttls':
                self.ssl = 'starttls'
            elif config_options['ssl'] == 'yes':
                print 'Warning: ssl=yes for email alerter is untested'
                self.ssl = 'yes'
        else:
            self.ssl = None

        self.mail_host = mail_host
        self.mail_port = mail_port
        self.from_addr = from_addr
        self.to_addr = to_addr

        self.support_catchup = True

    def send_alert(self, name, monitor):
        """Send the email."""

        type = self.should_alert(monitor)
        (days, hours, minutes, seconds) = self.get_downtime(monitor)

        if monitor.is_remote():
            host = " on %s " % monitor.running_on
        else:
            host = " on host %s" % self.hostname

        message = MIMEMultipart()
        message['From'] = self.from_addr
        message['To'] = self.to_addr

        if type == "":
            return
        elif type == "failure":
            message['Subject'] = "[%s] Monitor %s Failed!" % (self.hostname, name)
            body = """Monitor %s%s has failed.
            Failed at: %s
            Downtime: %d+%02d:%02d:%02d
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
            try:
                if monitor.recover_info != "":
                    body += "\nRecovery info: %s" % monitor.recover_info
            except AttributeError:
                body += "\nNo recovery info available"

        elif type == "success":
            message['Subject'] = "[%s] Monitor %s succeeded" % (self.hostname, name)
            body = "Monitor %s%s is back up.\nOriginally failed at: %s\nDowntime: %d+%02d:%02d:%02d\nDescription: %s" % (name, host, self.format_datetime(monitor.first_failure_time()), days, hours, minutes, seconds, monitor.describe())

        elif type == "catchup":
            message['Subject'] = "[%s] Monitor %s failed earlier!" % (self.from_addr, self.to_addr, self.hostname, name)
            body = "Monitor %s%s failed earlier while this alerter was out of hours.\nFailed at: %s\nVirtual failure count: %d\nAdditional info: %s\nDescription: %s" % (name, host, self.format_datetime(monitor.first_failure_time()), monitor.virtual_fail_count(), monitor.get_result(), monitor.describe())

        else:
            print "Unknown alert type %s" % type
            return

        message.attach(MIMEText(body, 'plain'))

        if not self.dry_run:
            try:
                if self.ssl is None or self.ssl == 'starttls':
                    server = smtplib.SMTP(self.mail_host, self.mail_port)
                elif self.ssl == 'yes':
                    server = smtplib.SMTP_SSL(self.mail_host, self.mail_port)

                if self.ssl == 'starttls':
                    server.starttls()

                if self.username is not None:
                    server.login(self.username, self.password)
                server.sendmail(self.from_addr, self.to_addr, message.as_string())
                server.quit()
            except Exception, e:
                print "Couldn't send mail:", e
                self.available = False
        else:
            print "dry_run: would send email: %s" % message.as_string()
