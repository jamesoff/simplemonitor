
from monitors import *

class SimpleMonitor:
    def __init__(self):
        """Main class turn on."""
        self.monitors = {}
        self.failed = []
        self.still_failing = []
        self.skipped = []
        self.warning = []

        self.loggers = {}
        self.statusers = {}
        self.alerters = {}

    def add_tcp_monitor(self, name, params):
        """Create a TCP connect monitor."""
        if len(params) != 2:
            raise RuntimeError("wrong parameter count")
        self.monitors[name] = MonitorTCP(params[0], params[1])

    def add_service_monitor(self, name, params):
        """Create a (Windows) service monitor."""
        if len(params) not in [2, 3]:
            raise RuntimeError("wrong parameter count")
        if len(params) == 2:
            self.monitors[name] = MonitorService(params[0], params[1], ".")
        else:
            self.monitors[name] = MonitorService(params[0], params[1], params[2])

    def add_rc_monitor(self, name, params):
        """Create an rc (FreeBSD Service) monitor."""
        if len(params) not in [1,3]:
            raise RuntimeError("wrong parameter count")
        if len(params) == 1:
            self.monitors[name] = MonitorRC(params[0])
        elif len(params) == 2:
            self.monitors[name] = MonitorRC(params[0], params[1])
        else:
            self.monitors[name] = MonitorRC(params[0], params[1], params[2])

    def add_host_monitor(self, name, host):
        """Create a host (ping) monitor."""
        self.monitors[name] = MonitorHost(host)

    def add_diskspace_monitor(self, name, partition, limit):
        """Create a diskspace monitor."""
        self.monitors[name] = MonitorDiskSpace(partition, limit)

    def add_http_monitor(self, name, url, regexp, allowed_codes = []):
        """Create an HTTP monitor."""
        self.monitors[name] = MonitorHTTP(url, regexp, allowed_codes)

    def add_apcupsd_monitor(self, name, path):
        """Create an apcupsd monitor."""
        self.monitors[name] = MonitorApcupsd(path)
    
    def add_monitor(self, name, monitor):
        self.monitors[name] = monitor

    def set_tolerance(self, monitor, tolerance):
        self.monitors[monitor].set_tolerance(tolerance)

    def set_urgency(self, monitor, urgency):
        self.monitors[monitor].set_urgency(urgency)

    def set_dependencies(self, name, dependencies):
        """Update a monitor's dependencies."""
        self.monitors[name].set_dependencies(dependencies)

    def reset_monitors(self):
        """Clear all the monitors' dependency info back to default."""
        [self.monitors[key].reset_dependencies() for key in self.monitors.keys()]

    def old_run_tests(self, verbose=False):
        """Magic time."""
        finished = False
        joblist = self.monitors.keys()
        failed = []
        skipped = []
        warning = []
        self.reset_monitors()

        if verbose:
            print "running tests..."
        while not finished:
            did_something = False
            for key in joblist:
                if verbose:
                    print "--> %s" % key
                deps = self.monitors[key].get_dependencies()
                if deps == []:
                    did_something = True
                    monitor = self.monitors[key]
                    monitor.run_test()
                    if monitor.state():
                        for key2 in self.monitors.keys():
                            if key2 == key:
                                continue
                            self.monitors[key2].dependency_succeeded(key)
                        joblist.remove(key)
                    else:
                        joblist.remove(key)
                        if self.monitors[key].test_success():
                            warning.append(key)
                        else:
                            failed.append(key)
            if not did_something:
                for key in joblist:
                    skipped.append(key)
                finished = True
            if len(joblist) == 0:
                finished = True

        # check if things that failed this time are new
        still_failing = []
        for key in failed:
            if not self.monitors[key].first_failure():
                still_failing.append(key)
        for key in still_failing:
            failed.remove(key)

        for key in failed:
            if verbose:
                print "new failure: %s" % key
                if self.monitors[key].get_result() != "":
                    print "  %s" % self.monitors[key].get_result()
        for key in still_failing:
            if verbose:
                print "re-failed: %s" % key
                if self.monitors[key].get_result() != "":
                    print "  %s" % self.monitors[key].get_result()
        for key in skipped:
            if verbose:
                print "skipped: %s" % key

        self.failed = failed
        self.still_failing = still_failing
        self.skipped = skipped
        self.warning = warning

    def run_tests(self, verbose=False):
        self.reset_monitors()

        joblist = self.monitors.keys()
        new_joblist = []
        failed = []

        finished = False
        not_run = False

        while len(joblist) > 0:
            skipped = []
            new_joblist = []
            for monitor in joblist:
                if len(self.monitors[monitor].get_dependencies()) > 0:
                    new_joblist.append(monitor)
                    for dep in self.monitors[monitor].get_dependencies():
                        if dep in failed:
                            if verbose:
                                print "Doesn't look like %s worked, skipping %s" % (dep, monitor)
                            failed.append(monitor)
                            self.monitors[monitor].record_skip(dep)
                            new_joblist.remove(monitor)
                    continue
                try:
                    if self.monitors[monitor].should_run():
                        not_run = False
                        self.monitors[monitor].run_test()
                    else:
                        not_run = True
                        if verbose:
                            print "Not run: %s" % monitor
                except Exception, e:
                    if verbose:
                        sys.stderr.write("Monitor %s threw exception during run_test(): %s\n" % (monitor, e))
                if self.monitors[monitor].get_error_count() > 0:
                    if self.monitors[monitor].virtual_fail_count() == 0:
                        if verbose:
                            print "Warning: %s" % monitor
                    else:
                        if verbose:
                            print "Fail: %s" % monitor
                    failed.append(monitor)
                else:
                    if verbose and not not_run:
                        print "Passed: %s" % monitor
                    for monitor2 in joblist:
                        self.monitors[monitor2].dependency_succeeded(monitor)
            joblist = new_joblist
        if verbose:
            print

    def _print_pretty_results(self, keys):
        """Private function used by pretty_results.
        Actually does the printing."""
        for service in keys:
            reason = self.monitors[service].get_result()
            if reason == "":
                print service
            else:
                print "%s (%s)" % (service, reason)

    def pretty_results(self):
        """Display the current state of our monitors in a human-readable fashion."""
        if len(self.warning + self.failed + self.still_failing + self.skipped):
            print
            print datetime.datetime.now().isoformat()

        if len(self.warning):
            print "--> Warnings:"
            self._print_pretty_results(self.warning)

        if len(self.failed):
            print "--> New failures:"
            self._print_pretty_results(self.failed)

        if len(self.still_failing):
            print "--> Still failing:"
            self._print_pretty_results(self.still_failing)

        if len(self.skipped):
            print "--> Skipped due to failed dependencies:"
            self._print_pretty_results(self.skipped)

    def log_result(self, logger):
        """Use the given logger object to log our state."""
        logger.check_dependencies(self.failed + self.still_failing + self.skipped)
        for key in self.monitors.keys():
            self.monitors[key].log_result(key, logger)

    def do_alert(self, alerter):
        """Use the given alerter object to send an alert, if needed."""
        alerter.check_dependencies(self.failed + self.still_failing + self.skipped)
        for key in self.monitors.keys():
            alerter.send_alert(key, self.monitors[key])

    def count_monitors(self):
        """Gets the number of monitors we have defined."""
        return len(self.monitors)

    def add_alerter(self, name, alerter):
        self.alerters[name] = alerter

    def add_logger(self, name, logger):
        self.loggers[name] = logger

    def add_statuser(self, name, statuser):
        self.statusers[name] = statuser
    
    def do_alerts(self):
        for key in self.alerters.keys():
            self.do_alert(self.alerters[key])

    def do_logs(self):
        for key in self.loggers.keys():
            self.log_result(self.loggers[key])

    def do_status(self):
        for key in self.statusers.keys():
            self.log_result(self.statusers[key])

