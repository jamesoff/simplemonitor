# coding=utf-8
"""Execution logic for SimpleMonitor."""

import copy
import logging
import pickle  # nosec
import sys
import time
from typing import Any, Dict, List

from .Alerters.alerter import Alerter
from .Loggers.logger import Logger
from .Monitors.monitor import Monitor, get_class

module_logger = logging.getLogger("simplemonitor")


class SimpleMonitor:
    def __init__(self, allow_pickle: bool = True) -> None:
        """Main class turn on."""
        self.allow_pickle = allow_pickle
        self.monitors = {}  # type: Dict[str, Monitor]
        self.failed = []  # type: List[str]
        self.still_failing = []  # type: List[str]
        self.skipped = []  # type: List[str]
        self.warning = []  # type: List[str]
        self.remote_monitors = {}  # type: Dict[str, Monitor]

        self.loggers = {}  # type: Dict[str, Logger]
        self.alerters = {}  # type: Dict[str, Alerter]

    def add_monitor(self, name: str, monitor: Monitor) -> None:
        self.monitors[name] = monitor

    def update_monitor_config(self, name: str, config_options: dict) -> None:
        self.monitors[name].__init__(name, config_options)  # type: ignore

    def update_logger_config(self, name: str, config_options: dict) -> None:
        self.loggers[name].__init__(config_options)  # type: ignore

    def update_alerter_config(self, name: str, config_options: dict) -> None:
        self.alerters[name].__init__(config_options)  # type: ignore

    def set_urgency(self, monitor: str, urgency: bool) -> None:
        self.monitors[monitor].urgent = urgency

    def has_monitor(self, monitor: str) -> bool:
        return monitor in self.monitors.keys()

    def has_logger(self, logger: str) -> bool:
        return logger in self.loggers.keys()

    def has_alerter(self, alerter: str) -> bool:
        return alerter in self.alerters.keys()

    def reset_monitors(self) -> None:
        """Clear all the monitors' dependency info back to default."""
        for key in list(self.monitors.keys()):
            self.monitors[key].reset_dependencies()

    def verify_dependencies(self) -> bool:
        ok = True
        for k in list(self.monitors.keys()):
            for dependency in self.monitors[k].dependencies:
                if dependency not in list(self.monitors.keys()):
                    module_logger.critical(
                        "Configuration error: dependency %s of monitor %s is not defined!",
                        dependency,
                        k,
                    )
                    ok = False
        return ok

    def verify_alerting(self) -> bool:
        """Sanity check the configuration to see if we have at least an alerter, or network logging."""
        sane = True
        if len(self.alerters) == 0:
            for _, logger in self.loggers.items():
                if logger._type == "network":
                    break
            else:
                sane = False
        return sane

    def sort_joblist(self, joblist: List[str]) -> List[str]:
        """Order a list of monitors so that compound monitors are at the end"""
        new_list = []  # type: List[str]
        late_list = []  # type: List[str]
        for monitor in joblist:
            if self.monitors[monitor]._type in ["compound"]:
                late_list.append(monitor)
            else:
                new_list.append(monitor)
        new_list.extend(late_list)
        return new_list

    def run_tests(self) -> None:
        self.reset_monitors()

        joblist = list(self.monitors.keys())
        joblist = self.sort_joblist(joblist)
        failed = []  # type: List[str]

        not_run = False

        while joblist:
            new_joblist = []  # type: List[str]
            module_logger.debug("Starting loop with joblist %s", joblist)
            for monitor in joblist:
                module_logger.debug("Trying monitor: %s", monitor)
                if self.monitors[monitor].remaining_dependencies:
                    # this monitor has outstanding deps, put it on the new joblist for next loop
                    new_joblist.append(monitor)
                    module_logger.debug(
                        "Added %s to new joblist, is now %s", monitor, new_joblist
                    )
                    for dep in self.monitors[monitor].remaining_dependencies:
                        module_logger.debug(
                            "considering %s's dependency %s (failed monitors: %s)",
                            monitor,
                            dep,
                            failed,
                        )
                        if dep in failed:
                            # oh wait, actually one of its deps failed, so we'll never be able to run it
                            module_logger.info(
                                "Doesn't look like %s worked, skipping %s", dep, monitor
                            )
                            failed.append(monitor)
                            self.monitors[monitor].record_skip(dep)
                            try:
                                new_joblist.remove(monitor)
                            except Exception:
                                module_logger.exception(
                                    "Exception caught while trying to remove monitor %s with failed deps from new joblist.",
                                    monitor,
                                )
                                module_logger.debug(
                                    "new_joblist is currently: %s", new_joblist
                                )
                            break
                    continue
                try:
                    if self.monitors[monitor].should_run():
                        not_run = False
                        start_time = time.time()
                        self.monitors[monitor].run_test()
                        end_time = time.time()
                        self.monitors[monitor].last_run_duration = int(
                            end_time - start_time
                        )
                    else:
                        not_run = True
                        self.monitors[monitor].record_skip(None)
                        module_logger.info("Not run: %s", monitor)
                except Exception:
                    module_logger.exception(
                        "Monitor %s threw exception during run_test()", monitor
                    )
                if self.monitors[monitor].error_count > 0:
                    if self.monitors[monitor].virtual_fail_count() == 0:
                        module_logger.warning(
                            "monitor failed but within tolerance: %s", monitor
                        )
                    else:
                        module_logger.error(
                            "monitor failed: %s (%s)",
                            monitor,
                            self.monitors[monitor].last_result,
                        )
                    failed.append(monitor)
                else:
                    if not not_run:
                        module_logger.info("monitor passed: %s", monitor)
                    for monitor2 in joblist:
                        self.monitors[monitor2].dependency_succeeded(monitor)
            joblist = copy.copy(new_joblist)

    def log_result(self, logger: Logger) -> None:
        """Use the given logger object to log our state."""
        logger.check_dependencies(self.failed + self.still_failing + self.skipped)
        logger.start_batch()
        for key in list(self.monitors.keys()):
            if self.monitors[key].group in logger._groups:
                logger.save_result2(key, self.monitors[key])
            else:
                module_logger.debug(
                    "not logging for %s due to group mismatch (monitor in group %s, logger has groups %s",
                    key,
                    self.monitors[key].group,
                    logger._groups,
                )
        try:
            for key in list(self.remote_monitors.keys()):
                logger.save_result2(key, self.remote_monitors[key])
        except Exception:  # pragma: no cover
            module_logger.exception("exception while logging remote monitors")
        logger.end_batch()

    def do_alert(self, alerter: Alerter) -> None:
        """Use the given alerter object to send an alert, if needed."""
        alerter.check_dependencies(self.failed + self.still_failing + self.skipped)
        for key in list(self.monitors.keys()):
            this_monitor = self.monitors[key]  # type: Monitor
            # Don't generate alerts for monitors which want it done remotely
            if this_monitor.remote_alerting:
                # TODO: could potentially disable alerts by setting a monitor to remote alerting, but not having anywhere to send it!
                module_logger.debug(
                    "skipping alert for monitor %s as it wants remote alerting", key
                )
                continue
            try:
                if this_monitor.group in alerter.groups:
                    # Only notifications for services that have it enabled
                    if this_monitor.notify:
                        module_logger.debug("notifying alerter %s", alerter.name)
                        alerter.send_alert(key, self.monitors[key])
                    else:
                        module_logger.info(
                            "skipping alerters for disabled monitor %s", key
                        )
                else:
                    module_logger.info(
                        "skipping alerter %s as monitor %s is not in group %s",
                        alerter.name,
                        this_monitor.name,
                        alerter.groups,
                    )
            except Exception:  # pragma: no cover
                module_logger.exception("exception caught while alerting for %s", key)
        for key in list(self.remote_monitors.keys()):
            this_monitor = self.remote_monitors[key]
            try:
                if this_monitor.remote_alerting:
                    alerter.send_alert(key, this_monitor)
                else:
                    module_logger.debug(
                        "not alerting for monitor %s as it doesn't want remote alerts",
                        key,
                    )
            except Exception:  # pragma: no cover
                module_logger.exception(
                    "exception caught while alerting for remote monitor %s", key
                )

    def count_monitors(self) -> int:
        """Gets the number of monitors we have defined."""
        return len(self.monitors)

    def add_alerter(self, name: str, alerter: Alerter) -> None:
        self.alerters[name] = alerter

    def add_logger(self, name: str, logger: Logger) -> None:
        if isinstance(logger, Logger):
            self.loggers[name] = logger
        else:
            module_logger.critical(
                "Failed to add logger because it is not the right type"
            )

    def prune_monitors(self, retain: List[str]) -> None:
        """Remove monitors which are in our list but not in the list passed to us.

        Used to tidy up after a config reload (which may have removed monitors)"""
        delete_list = []
        for monitor in self.monitors:
            if monitor not in retain:
                module_logger.info("Removing monitor %s", monitor)
                delete_list.append(monitor)
        for monitor in delete_list:
            del self.monitors[monitor]
        if not self.verify_dependencies():
            module_logger.critical(
                "Broken dependencies after pruning monitors, aborting!"
            )
            sys.exit(1)

    def prune_alerters(self, retain: List[str]) -> None:
        """Remove alerters which are in our list but not in the list passed to us.

        Used to tidy up after a config reload (which may have removed alerters)"""
        delete_list = []
        for alerter in self.alerters:
            if alerter not in retain:
                module_logger.info("Removing alerter %s", alerter)
                delete_list.append(alerter)
        for alerter in delete_list:
            del self.alerters[alerter]

    def prune_loggers(self, retain: List[str]) -> None:
        """Remove loggers which are in our list but not in the list passed to us.

        Used to tidy up after a config reload (which may have removed logger)"""
        delete_list = []
        for logger in self.loggers:
            if logger not in retain:
                module_logger.info("Removing logger %s", logger)
                delete_list.append(logger)
        for logger in delete_list:
            del self.loggers[logger]

    def do_alerts(self) -> None:
        for key in list(self.alerters.keys()):
            self.do_alert(self.alerters[key])

    def do_recovery(self) -> None:
        for key in list(self.monitors.keys()):
            self.monitors[key].attempt_recover()

    def do_recovered(self) -> None:
        for key in list(self.monitors.keys()):
            self.monitors[key].run_recovered()

    def hup_loggers(self) -> None:
        for logger in self.loggers:
            self.loggers[logger].hup()

    def do_logs(self) -> None:
        for key in list(self.loggers.keys()):
            self.log_result(self.loggers[key])

    def update_remote_monitor(self, data: Any, hostname: str) -> None:
        for (name, state) in data.items():
            module_logger.info("updating remote monitor %s", name)
            if isinstance(state, dict):
                remote_monitor = get_class(state["cls_type"]).from_python_dict(
                    state["data"]
                )
                self.remote_monitors[name] = remote_monitor
            elif self.allow_pickle:
                # Fallback for old remote monitors
                try:
                    remote_monitor = pickle.loads(state)  # nosec
                except pickle.UnpicklingError:
                    module_logger.critical("Could not unpickle monitor %s", name)
                else:
                    self.remote_monitors[name] = remote_monitor
            else:
                module_logger.critical(
                    "Could not deserialize state of monitor %s. "
                    "If the remote host uses an old version of "
                    "simplemonitor, you need to set allow_pickle = true "
                    "in the [monitor] section.",
                    name,
                )

    def run_loop(self) -> None:
        """Run the complete monitor loop once."""
        module_logger.debug("Running tests")
        self.run_tests()
        module_logger.debug("Running recovery")
        self.do_recovery()
        self.do_recovered()
        module_logger.debug("Running alerts")
        self.do_alerts()
        module_logger.debug("Running logs")
        self.do_logs()
        module_logger.debug("Loop complete")
