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

    days = range(0,7)
    times_type = "always"
    time_info = [None, None]

    debug = False
    verbose = False

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

        if config_options.has_key("debug_times"):
            self.time_info = [
                    (datetime.datetime.now() - datetime.timedelta(minutes=1)).time(),
                    (datetime.datetime.now() + datetime.timedelta(minutes=1)).time()
            ]
            print "debug: set times for alerter to", self.time_info

    def format_datetime(self, dt):
        """Return an isoformat()-like datetime without the microseconds."""
        dt = dt.replace(microsecond = 0)
        return dt.isoformat(" ")

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

        #print out_of_hours

        if monitor.virtual_fail_count() > 0:
            if self.debug:
                print "alerter %s: monitor %s has failed" % (self.name, monitor.name)
            #print self.ooh_failures
            # Monitor has failed (not just first time)
            if self.delay_notification:
                #print "alerter %s: i support delay notification" % self.name
                #print not out_of_hours
                if not out_of_hours:
                    #print "alerter %s: i'm not out of hours" % self.name
                    if monitor.name in self.ooh_failures:
                        #print "alerter %s: monitor %s is listed as having failed ooh" % (self.name, monitor.name), self.ooh_failures
                        try:
                            self.ooh_failures.remove(monitor.name)
                        except:
                            print "Warning: Couldn't remove %s from OOH list; will maybe generate too many alerts." % monitor.name
                        if self.support_catchup:
                            #print "alerter %s: i support catchup, so catching up" % self.name
                            return "catchup"
                        else:
                            return "failure"
            if monitor.virtual_fail_count() == self.limit:
                #print "alerter %s: monitor %s has failed enough times to trigger us" % (self.name, monitor.name)
                # This is the first time we've failed
                if out_of_hours:
                    #print "alerter %s: i'm out of hours" % self.name
                    if monitor.name not in self.ooh_failures:
                        self.ooh_failures.append(monitor.name)
                        return ""
                return "failure"
            return ""
        elif monitor.all_better_now() and monitor.last_virtual_fail_count() >= self.limit:
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
        #print "days are", self.days
        #print "today is %d" % datetime.datetime.now().weekday()
        if datetime.datetime.now().weekday() not in self.days:
            #print "not allowed today"
            return False
        return True

    def allowed_time(self):
        """Check if now is an allowed time for an alert."""
        if self.times_type == "always":
            return True
        now = datetime.datetime.now().time()
        #print "now is", now
        if self.times_type == "only":
            if (now > self.time_info[0]) and (now < self.time_info[1]):
                return True
            else:
                return False
        elif self.times_type == "not":
            if (now > self.time_info[0]) and (now < self.time_info[1]):
                #print "not: not allowed"
                return False
            else:
                #print "not: allowed"
                return True
        else:
            print "This should never happen! Unknown times_type in alerter."
            return True

