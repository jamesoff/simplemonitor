import sys
import signal
import copy
import pickle
import datetime
import time


class SimpleMonitor:

    # TODO: move this outside into monitor.py?
    #      could give better control over restarting the listener thread
    need_hup = False
    verbose = False
    debug = False

    def __init__(self):
        """Main class turn on."""
        self.monitors = {}
        self.failed = []
        self.still_failing = []
        self.skipped = []
        self.warning = []
        self.remote_monitors = {}

        self.loggers = {}
        self.alerters = {}

        try:
            signal.signal(signal.SIGHUP, self.hup_loggers)
        except:
            sys.stderr.write("Unable to trap SIGHUP... maybe it doesn't exist on this platform.\n")

    def hup_loggers(self, sig_number, stack_frame):
        """Handle a SIGHUP (rotate logfiles).

        We set a variable to say we want to do this later (so it's done at the right time)."""

        self.need_hup = True
        print "We get signal."

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

    def verify_dependencies(self):
        ok = True
        for k in self.monitors.keys():
            for dependency in self.monitors[k]._dependencies:
                if dependency not in self.monitors.keys():
                    print "Configuration error: dependency %s of monitor %s is not defined!" % (dependency, k)
                    ok = False
        return ok

    def set_verbosity(self, verbose, debug):
        self.verbose = verbose
        self.debug = debug

    def run_tests(self):
        self.reset_monitors()
        verbose = self.verbose
        debug = self.debug

        joblist = self.monitors.keys()
        new_joblist = []
        failed = []

        not_run = False

        while len(joblist) > 0:
            new_joblist = []
            if debug:
                print "\nStarting loop:", joblist
            for monitor in joblist:
                if debug:
                    print "Trying: %s" % monitor
                if len(self.monitors[monitor].get_dependencies()) > 0:
                    # this monitor has outstanding deps, put it on the new joblist for next loop
                    new_joblist.append(monitor)
                    if debug:
                        print "added %s to new joblist, is now" % monitor, new_joblist
                    for dep in self.monitors[monitor].get_dependencies():
                        if debug:
                            print "  considering %s's dependency %s" % (monitor, dep), failed
                        if dep in failed:
                            # oh wait, actually one of its deps failed, so we'll never be able to run it
                            if verbose:
                                print "Doesn't look like %s worked, skipping %s" % (dep, monitor)
                            failed.append(monitor)
                            self.monitors[monitor].record_skip(dep)
                            try:
                                new_joblist.remove(monitor)
                            except:
                                print "Exception caught while trying to remove monitor %s with failed deps from new joblist." % monitor
                                if debug:
                                    print "new_joblist is currently", new_joblist
                            break
                    continue
                try:
                    if self.monitors[monitor].should_run():
                        not_run = False
                        start_time = time.time()
                        self.monitors[monitor].run_test()
                        end_time = time.time()
                        self.monitors[monitor].last_run_duration = end_time - start_time
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
                            print "Fail: %s (%s)" % (monitor, self.monitors[monitor].last_result)
                    failed.append(monitor)
                else:
                    if verbose and not not_run:
                        print "Passed: %s" % monitor
                    for monitor2 in joblist:
                        self.monitors[monitor2].dependency_succeeded(monitor)
            joblist = copy.copy(new_joblist)
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
        logger.start_batch()
        for key in self.monitors.keys():
            self.monitors[key].log_result(key, logger)
        try:
            for key in self.remote_monitors.keys():
                self.remote_monitors[key].log_result(key, logger)
        except:
            print "exception while logging remote monitors"
        logger.end_batch()

    def do_alert(self, alerter):
        """Use the given alerter object to send an alert, if needed."""
        alerter.check_dependencies(self.failed + self.still_failing + self.skipped)
        for key in self.monitors.keys():
            # Don't generate alerts for monitors which want it done remotely
            if self.monitors[key].remote_alerting:
                # TODO: could potentially disable alerts by setting a monitor to remote alerting, but not having anywhere to send it!
                if self.debug:
                    print "skipping alert for monitor %s as it wants remote alerting" % key
                continue
            try:
                alerter.send_alert(key, self.monitors[key])
            except Exception, e:
                print "exception caught while alerting for %s: %s" % (key, e)
        for key in self.remote_monitors.keys():
            try:
                if self.remote_monitors[key].remote_alerting:
                    alerter.send_alert(key, self.remote_monitors[key])
                else:
                    if self.debug:
                        print "not alerting for monitor %s as it doesn't want remote alerts" % key
                    continue
            except Exception, e:
                print "exception caught while alerting for %s: %s" % (key, e)

    def count_monitors(self):
        """Gets the number of monitors we have defined."""
        return len(self.monitors)

    def add_alerter(self, name, alerter):
        self.alerters[name] = alerter

    def add_logger(self, name, logger):
        self.loggers[name] = logger

    def do_alerts(self):
        for key in self.alerters.keys():
            self.do_alert(self.alerters[key])

    def do_recovery(self):
        for key in self.monitors.keys():
            self.monitors[key].attempt_recover()

    def do_logs(self):
        if self.need_hup:
            print "Processing HUP."
            for logger in self.loggers:
                self.loggers[logger].hup()
            self.need_hup = False

        for key in self.loggers.keys():
            self.log_result(self.loggers[key])

    def update_remote_monitor(self, data, hostname):
        for monitor in data.keys():
            if self.debug:
                print "trying remote monitor %s" % monitor
            self.remote_monitors[monitor] = pickle.loads(data[monitor])
