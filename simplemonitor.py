# coding=utf-8

import signal
import copy
import pickle
import time
import logging

import Loggers

module_logger = logging.getLogger('simplemonitor')


class SimpleMonitor:

    # TODO: move this outside into monitor.py?
    #      could give better control over restarting the listener thread
    need_hup = False

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
            module_logger.warning("Unable to trap SIGHUP... maybe it doesn't exist on this platform.\n")

    def hup_loggers(self, sig_number, stack_frame):
        """Handle a SIGHUP (rotate logfiles).

        We set a variable to say we want to do this later (so it's done at the right time)."""

        self.need_hup = True
        module_logger.info("We get signal.")

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
                    module_logger.critical("Configuration error: dependency %s of monitor %s is not defined!", dependency, k)
                    ok = False
        return ok

    def run_tests(self):
        self.reset_monitors()

        joblist = list(self.monitors.keys())
        new_joblist = []
        failed = []

        not_run = False

        while len(joblist) > 0:
            new_joblist = []
            module_logger.debug("Starting loop with joblist %s", joblist)
            for monitor in joblist:
                module_logger.debug("Trying monitor: %s", monitor)
                if len(self.monitors[monitor].get_dependencies()) > 0:
                    # this monitor has outstanding deps, put it on the new joblist for next loop
                    new_joblist.append(monitor)
                    module_logger.debug("Added %s to new joblist, is now %s", monitor, new_joblist)
                    for dep in self.monitors[monitor].get_dependencies():
                        module_logger.debug("considering %s's dependency %s (failed monitors: %s)", monitor, dep, failed)
                        if dep in failed:
                            # oh wait, actually one of its deps failed, so we'll never be able to run it
                            module_logger.info("Doesn't look like %s worked, skipping %s", dep, monitor)
                            failed.append(monitor)
                            self.monitors[monitor].record_skip(dep)
                            try:
                                new_joblist.remove(monitor)
                            except Exception:
                                module_logger.exception("Exception caught while trying to remove monitor %s with failed deps from new joblist.", monitor)
                                module_logger.debug("new_joblist is currently: %s", new_joblist)
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
                        module_logger.info("Not run: %s", monitor)
                except Exception as e:
                    module_logger.exception("Monitor %s threw exception during run_test()", monitor)
                if self.monitors[monitor].get_error_count() > 0:
                    if self.monitors[monitor].virtual_fail_count() == 0:
                        module_logger.warning("monitor failed but within tolerance: %s", monitor)
                    else:
                        module_logger.error("monitor failed: %s (%s)", monitor, self.monitors[monitor].last_result)
                    failed.append(monitor)
                else:
                    if not not_run:
                        module_logger.info("monitor passed: %s", monitor)
                    for monitor2 in joblist:
                        self.monitors[monitor2].dependency_succeeded(monitor)
            joblist = copy.copy(new_joblist)

    def log_result(self, logger):
        """Use the given logger object to log our state."""
        logger.check_dependencies(self.failed + self.still_failing + self.skipped)
        logger.start_batch()
        for key in list(self.monitors.keys()):
            self.monitors[key].log_result(key, logger)
        try:
            for key in list(self.remote_monitors.keys()):
                module_logger.info('remote logging for %s', key)
                self.remote_monitors[key].log_result(key, logger)
        except Exception:
            module_logger.exception("exception while logging remote monitors")
        logger.end_batch()

    def do_alert(self, alerter):
        """Use the given alerter object to send an alert, if needed."""
        alerter.check_dependencies(self.failed + self.still_failing + self.skipped)
        for key in list(self.monitors.keys()):
            # Don't generate alerts for monitors which want it done remotely
            if self.monitors[key].remote_alerting:
                # TODO: could potentially disable alerts by setting a monitor to remote alerting, but not having anywhere to send it!
                module_logger.debug("skipping alert for monitor %s as it wants remote alerting", key)
                continue
            module_logger.debug("considering alert for monitor %s (group: %s) with alerter %s (groups: %s)",
                                self.monitors[key].name,
                                self.monitors[key].group,
                                alerter.name,
                                alerter.groups
                                )
            try:
                if self.monitors[key].group in alerter.groups:
                    # Only notifications for services that have it enabled
                    if self.monitors[key].notify:
                        module_logger.debug("notifying alerter %s", alerter.name)
                        alerter.send_alert(key, self.monitors[key])
                    else:
                        module_logger.info("skipping alerters for disabled monitor %s", key)
                else:
                    module_logger.info("skipping alerter %s as monitor is not in group", alerter.name)
            except Exception as e:
                module_logger.exception("exception caught while alerting for %s", key)
        for key in list(self.remote_monitors.keys()):
            try:
                if self.remote_monitors[key].remote_alerting:
                    alerter.send_alert(key, self.remote_monitors[key])
                else:
                    module_logger.debug("not alerting for monitor %s as it doesn't want remote alerts", key)
                    continue
            except Exception as e:
                module_logger.exception("exception caught while alerting for %s", key)

    def count_monitors(self):
        """Gets the number of monitors we have defined."""
        return len(self.monitors)

    def add_alerter(self, name, alerter):
        self.alerters[name] = alerter

    def add_logger(self, name, logger):
        if isinstance(logger, Loggers.logger.Logger):
            self.loggers[name] = logger
        else:
            module_logger.critical('Failed to add logger because it is not the right type')

    def do_alerts(self):
        for key in list(self.alerters.keys()):
            self.do_alert(self.alerters[key])

    def do_recovery(self):
        for key in list(self.monitors.keys()):
            self.monitors[key].attempt_recover()

    def do_logs(self):
        if self.need_hup:
            module_logger.info("Processing HUP.")
            for logger in self.loggers:
                self.loggers[logger].hup()
            self.need_hup = False

        for key in list(self.loggers.keys()):
            self.log_result(self.loggers[key])

    def update_remote_monitor(self, data, hostname):
        for monitor in list(data.keys()):
            module_logger.info("trying remote monitor %s", monitor)
            self.remote_monitors[monitor] = pickle.loads(data[monitor])
