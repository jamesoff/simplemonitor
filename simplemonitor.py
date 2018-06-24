# coding=utf-8
"""Execution logic for SimpleMonitor."""

import signal
import copy
import pickle
import time
import logging
from socket import gethostname

import Loggers
import Monitors.monitor
import Monitors.network
import Monitors.service
import Monitors.host
import Monitors.file
import Monitors.compound
import Alerters

from envconfig import EnvironmentAwareConfigParser
from util import get_config_dict

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
        except ValueError:
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
        for key in list(self.monitors.keys()):
            self.monitors[key].reset_dependencies()

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

        while joblist:
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

    def load_monitors(self, filename):
        """Load all the monitors from the config file and return a populated SimpleMonitor."""
        config = EnvironmentAwareConfigParser()
        config.read(filename)
        monitors = config.sections()
        if "defaults" in monitors:
            default_config = get_config_dict(config, "defaults")
            monitors.remove("defaults")
        else:
            default_config = {}

        myhostname = gethostname().lower()

        module_logger.info('=== Loading monitors')
        for monitor in monitors:
            if config.has_option(monitor, "runon"):
                if myhostname != config.get(monitor, "runon").lower():
                    module_logger.warning("Ignoring monitor %s because it's only for host %s", monitor, config.get(monitor, "runon"))
                    continue
            monitor_type = config.get(monitor, "type")
            new_monitor = None
            config_options = default_config.copy()
            config_options.update(get_config_dict(config, monitor))

            if monitor_type == "host":
                new_monitor = Monitors.network.MonitorHost(monitor, config_options)

            elif monitor_type == "service":
                new_monitor = Monitors.service.MonitorService(monitor, config_options)

            elif monitor_type == "tcp":
                new_monitor = Monitors.network.MonitorTCP(monitor, config_options)

            elif monitor_type == "rc":
                new_monitor = Monitors.service.MonitorRC(monitor, config_options)

            elif monitor_type == "diskspace":
                new_monitor = Monitors.host.MonitorDiskSpace(monitor, config_options)

            elif monitor_type == "http":
                new_monitor = Monitors.network.MonitorHTTP(monitor, config_options)

            elif monitor_type == "apcupsd":
                new_monitor = Monitors.host.MonitorApcupsd(monitor, config_options)

            elif monitor_type == "svc":
                new_monitor = Monitors.service.MonitorSvc(monitor, config_options)

            elif monitor_type == "backup":
                new_monitor = Monitors.file.MonitorBackup(monitor, config_options)

            elif monitor_type == "portaudit":
                new_monitor = Monitors.host.MonitorPortAudit(monitor, config_options)

            elif monitor_type == "pkgaudit":
                new_monitor = Monitors.host.MonitorPkgAudit(monitor, config_options)

            elif monitor_type == "loadavg":
                new_monitor = Monitors.host.MonitorLoadAvg(monitor, config_options)

            elif monitor_type == "eximqueue":
                new_monitor = Monitors.service.MonitorEximQueue(monitor, config_options)

            elif monitor_type == "windowsdhcp":
                new_monitor = Monitors.service.MonitorWindowsDHCPScope(monitor, config_options)

            elif monitor_type == "zap":
                new_monitor = Monitors.host.MonitorZap(monitor, config_options)

            elif monitor_type == "fail":
                new_monitor = Monitors.monitor.MonitorFail(monitor, config_options)

            elif monitor_type == "null":
                new_monitor = Monitors.monitor.MonitorNull(monitor, config_options)

            elif monitor_type == "filestat":
                new_monitor = Monitors.host.MonitorFileStat(monitor, config_options)

            elif monitor_type == "compound":
                new_monitor = Monitors.compound.CompoundMonitor(monitor, config_options)
                new_monitor.set_mon_refs(self)

            elif monitor_type == 'dns':
                new_monitor = Monitors.network.MonitorDNS(monitor, config_options)

            elif monitor_type == 'command':
                new_monitor = Monitors.host.MonitorCommand(monitor, config_options)

            else:
                module_logger.error("Unknown type %s for monitor %s", monitor_type, monitor)
                continue
            if new_monitor is None:
                continue

            module_logger.info("Adding %s monitor %s: %s", monitor_type, monitor, new_monitor)
            self.add_monitor(monitor, new_monitor)

        for i in list(self.monitors.keys()):
            self.monitors[i].post_config_setup()
        module_logger.info('--- Loaded %d monitors', self.count_monitors())

    def load_loggers(self, config):
        """Load the loggers listed in the config object."""

        if config.has_option("reporting", "loggers"):
            loggers = config.get("reporting", "loggers").split(",")
        else:
            loggers = []

        module_logger.info('=== Loading loggers')
        for config_logger in loggers:
            logger_type = config.get(config_logger, "type")
            config_options = get_config_dict(config, config_logger)
            config_options['_name'] = config_logger
            if logger_type == "db":
                new_logger = Loggers.db.DBFullLogger(config_options)
            elif logger_type == "dbstatus":
                new_logger = Loggers.db.DBStatusLogger(config_options)
            elif logger_type == "logfile":
                new_logger = Loggers.file.FileLogger(config_options)
            elif logger_type == "html":
                new_logger = Loggers.file.HTMLLogger(config_options)
            elif logger_type == "network":
                new_logger = Loggers.network.NetworkLogger(config_options)
            elif logger_type == "json":
                new_logger = Loggers.file.JsonLogger(config_options)
            else:
                module_logger.error("Unknown logger logger_type %s", logger_type)
                continue
            if new_logger is None:
                module_logger.error("Creating logger %s failed!", new_logger)
                continue
            module_logger.info("Adding %s logger %s: %s", logger_type, config_logger, new_logger)
            self.add_logger(config_logger, new_logger)
            del new_logger
        module_logger.info('--- Loaded %d loggers', len(self.loggers))

    def load_alerters(monitor_instance, config):
        """Load the alerters listed in the config object."""
        if config.has_option("reporting", "alerters"):
            alerters = config.get("reporting", "alerters").split(",")
        else:
            alerters = []

        module_logger.info('=== Loading alerters')
        for alerter in alerters:
            alerter_type = config.get(alerter, "type")
            config_options = get_config_dict(config, alerter)
            if alerter_type == "email":
                new_alerter = Alerters.mail.EMailAlerter(config_options)
            elif alerter_type == "ses":
                new_alerter = Alerters.ses.SESAlerter(config_options)
            elif alerter_type == "bulksms":
                new_alerter = Alerters.bulksms.BulkSMSAlerter(config_options)
            elif alerter_type == "46elks":
                new_alerter = Alerters.fortysixelks.FortySixElksAlerter(config_options)
            elif alerter_type == "syslog":
                new_alerter = Alerters.syslogger.SyslogAlerter(config_options)
            elif alerter_type == "execute":
                new_alerter = Alerters.execute.ExecuteAlerter(config_options)
            elif alerter_type == "slack":
                new_alerter = Alerters.slack.SlackAlerter(config_options)
            elif alerter_type == "pushover":
                new_alerter = Alerters.pushover.PushoverAlerter(config_options)
            elif alerter_type == "nma":
                new_alerter = Alerters.nma.NMAAlerter(config_options)
            elif alerter_type == "pushbullet":
                new_alerter = Alerters.pushbullet.PushbulletAlerter(config_options)
            else:
                module_logger.error("Unknown alerter type %s", alerter_type)
                continue
            module_logger.info("Adding %s alerter %s", alerter_type, alerter)
            new_alerter.name = alerter
            monitor_instance.add_alerter(alerter, new_alerter)
            del new_alerter
        module_logger.info('--- Loaded %d alerters', len(monitor_instance.alerters))
