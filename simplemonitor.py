# coding=utf-8
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
        except Exception:
            sys.stderr.write("Unable to trap SIGHUP... maybe it doesn't exist on this platform.\n")

    def hup_loggers(self, sig_number, stack_frame):
        """Handle a SIGHUP (rotate logfiles).

        We set a variable to say we want to do this later (so it's done at the right time)."""

        self.need_hup = True
        print("We get signal.")

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
        [self.monitors[key].reset_dependencies() for key in list(self.monitors.keys())]

    def verify_dependencies(self):
        ok = True
        for k in list(self.monitors.keys()):
            for dependency in self.monitors[k]._dependencies:
                if dependency not in list(self.monitors.keys()):
                    print("Configuration error: dependency %s of monitor %s is not defined!" % (dependency, k))
                    ok = False
        return ok

    def set_verbosity(self, verbose, debug):
        self.verbose = verbose
        self.debug = debug
        if self.debug:
            self.verbose = True

    def run_tests(self):
        self.reset_monitors()
        verbose = self.verbose
        debug = self.debug

        joblist = list(self.monitors.keys())
        new_joblist = []
        failed = []

        not_run = False

        while len(joblist) > 0:
            new_joblist = []
            if debug:
                print("\nStarting loop:", joblist)
            for monitor in joblist:
                if debug:
                    print("Trying: %s" % monitor)
                if len(self.monitors[monitor].get_dependencies()) > 0:
                    # this monitor has outstanding deps, put it on the new joblist for next loop
                    new_joblist.append(monitor)
                    if debug:
                        print("added %s to new joblist, is now" % monitor, new_joblist)
                    for dep in self.monitors[monitor].get_dependencies():
                        if debug:
                            print("  considering %s's dependency %s" % (monitor, dep), failed)
                        if dep in failed:
                            # oh wait, actually one of its deps failed, so we'll never be able to run it
                            if verbose:
                                print("Doesn't look like %s worked, skipping %s" % (dep, monitor))
                            failed.append(monitor)
                            self.monitors[monitor].record_skip(dep)
                            try:
                                new_joblist.remove(monitor)
                            except Exception:
                                print("Exception caught while trying to remove monitor %s with failed deps from new joblist." % monitor)
                                if debug:
                                    print("new_joblist is currently", new_joblist)
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
                        self.monitors[monitor].record_skip(None)
                        if verbose:
                            print("Not run: %s" % monitor)
                except Exception as e:
                    if verbose:
                        sys.stderr.write("Monitor %s threw exception during run_test(): %s\n" % (monitor, e))
                if self.monitors[monitor].get_error_count() > 0:
                    if self.monitors[monitor].virtual_fail_count() == 0:
                        if verbose:
                            print("Warning: %s" % monitor)
                    else:
                        if verbose:
                            print("Fail: %s (%s)" % (monitor, self.monitors[monitor].last_result))
                    failed.append(monitor)
                else:
                    if verbose and not not_run:
                        print("Passed: %s" % monitor)
                    for monitor2 in joblist:
                        self.monitors[monitor2].dependency_succeeded(monitor)
            joblist = copy.copy(new_joblist)
        if verbose:
            print()

    def log_result(self, logger):
        """Use the given logger object to log our state."""
        logger.check_dependencies(self.failed + self.still_failing + self.skipped)
        logger.start_batch()
        for key in list(self.monitors.keys()):
            self.monitors[key].log_result(key, logger)
        try:
            for key in list(self.remote_monitors.keys()):
                print('remote logging for {0}'.format(key))
                self.remote_monitors[key].log_result(key, logger)
        except Exception:
            print("exception while logging remote monitors")
        logger.end_batch()

    def do_alert(self, alerter):
        """Use the given alerter object to send an alert, if needed."""
        alerter.check_dependencies(self.failed + self.still_failing + self.skipped)
        for key in list(self.monitors.keys()):
            if self.debug:
                print("{0}({1}) -> {2}({3})".format(self.monitors[key].name, self.monitors[key].group, alerter.name, alerter.groups))
            # Don't generate alerts for monitors which want it done remotely
            if self.monitors[key].remote_alerting:
                # TODO: could potentially disable alerts by setting a monitor to remote alerting, but not having anywhere to send it!
                if self.debug:
                    print("skipping alert for monitor %s as it wants remote alerting" % key)
                continue
            try:
                if self.monitors[key].group in alerter.groups:
                    # Only notifications for services that have it enabled
                    if self.monitors[key].notify:
                        if self.debug:
                            print("  - Notifying alerter: {0}".format(alerter.name))
                        alerter.send_alert(key, self.monitors[key])
                    else:
                        if self.debug:
                            print("  - Skipping alerters: Monitor Disabled")
                else:
                    if self.debug:
                        print(" - Skipping alerter: {0}".format(alerter.name))
            except Exception as e:
                print("exception caught while alerting for %s: %s" % (key, e))
        for key in list(self.remote_monitors.keys()):
            try:
                if self.remote_monitors[key].remote_alerting:
                    alerter.send_alert(key, self.remote_monitors[key])
                else:
                    if self.debug:
                        print("not alerting for monitor %s as it doesn't want remote alerts" % key)
                    continue
            except Exception as e:
                print("exception caught while alerting for %s: %s" % (key, e))

    def count_monitors(self):
        """Gets the number of monitors we have defined."""
        return len(self.monitors)

    def add_alerter(self, name, alerter):
        self.alerters[name] = alerter

    def add_logger(self, name, logger):
        self.loggers[name] = logger

    def do_alerts(self):
        for key in list(self.alerters.keys()):
            self.do_alert(self.alerters[key])

    def do_recovery(self):
        for key in list(self.monitors.keys()):
            self.monitors[key].attempt_recover()

    def do_logs(self):
        if self.need_hup:
            print("Processing HUP.")
            for logger in self.loggers:
                self.loggers[logger].hup()
            self.need_hup = False

        for key in list(self.loggers.keys()):
            self.log_result(self.loggers[key])

    def update_remote_monitor(self, data, hostname):
        for monitor in list(data.keys()):
            if self.debug:
                print("trying remote monitor %s" % monitor)
            self.remote_monitors[monitor] = pickle.loads(data[monitor])
