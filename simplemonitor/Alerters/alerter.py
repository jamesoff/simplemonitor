# coding=utf-8
"""Alerting for SimpleMonitor"""

import datetime
import logging
import textwrap
from enum import Enum
from socket import gethostname
from typing import Any, List, NoReturn, Optional, Tuple, Union, cast

import arrow

from ..Monitors.monitor import Monitor
from ..util import (
    AlerterConfigurationError,
    MonitorState,
    format_datetime,
    get_config_option,
    subclass_dict_handler,
)


class AlertType(Enum):
    """What type of alert should be sent"""

    NONE = "none"
    FAILURE = "failure"
    CATCHUP = "catchup"
    SUCCESS = "success"


class AlertTimeFilter(Enum):
    """How should the Alerter times be handled"""

    ALWAYS = 0  # specified times are meaningless
    NOT = 1  # not allowed between the specified times
    ONLY = 2  # only allowed between the specified times


class AlertLength(Enum):
    """How long should an Alert message be?"""

    NOTIFICATION = 0  # "Monitor has failed"
    SMS = 1  # <= 140 chars
    ONELINE = 5  # SMS but not length limited
    TERSE = 2  # Short but multiline
    FULL = 3  # Multiline
    ESSAY = 4  # Everything


class Alerter:
    """BaseClass for Alerters"""

    _type = "unknown"
    _dependencies = None  # type: List[str]
    hostname = gethostname()
    available = False

    name = None  # type: Optional[str]

    _ooh_failures = None  # type: Optional[List[str]]
    # subclasses should set this to true if they support catchup notifications for delays
    support_catchup = False

    def __init__(self, config_options: dict = None) -> None:
        if config_options is None:
            config_options = {}
        self._config_options = config_options
        self.alerter_logger = logging.getLogger("simplemonitor.alerter-" + self._type)
        self.available = True
        self.name = cast(str, self.get_config_option("name", default="unamed"))
        self.dependencies = cast(
            List[str],
            self.get_config_option("depend", required_type="[str]", default=[]),
        )
        # require this many failures before firing
        self._limit = cast(
            int,
            self.get_config_option("limit", required_type="int", minimum=1, default=1),
        )
        # fire every time, rather than just once when the Monitor fails
        self._repeat = self.get_config_option(
            "repeat", required_type="int", default=0, minimum=0
        )
        # only fire for Monitors with one of these groups
        self._groups = self.get_config_option(
            "groups", required_type="[str]", default=["default"]
        )
        _times_type = cast(
            str,
            self.get_config_option(
                "times_type",
                required_type="str",
                allowed_values=["always", "only", "not"],
                default="always",
            ),
        )
        self._times_type = AlertTimeFilter.ALWAYS  # type: AlertTimeFilter
        if _times_type == "always":
            self._times_type = AlertTimeFilter.ALWAYS
        elif _times_type == "only":
            self._times_type = AlertTimeFilter.ONLY
        elif _times_type == "not":
            self._times_type = AlertTimeFilter.NOT
        else:
            raise ValueError("times_type is not recongnised: {}".format(_times_type))
        self._time_info = (
            None,
            None,
        )  # type: Tuple[Optional[datetime.time], Optional[datetime.time]]
        if self._times_type in [AlertTimeFilter.ONLY, AlertTimeFilter.NOT]:
            time_lower = str(
                self.get_config_option("time_lower", required_type="str", required=True)
            )
            time_upper = str(
                self.get_config_option("time_upper", required_type="str", required=True)
            )
            try:
                time_info = [
                    datetime.time(
                        int(time_lower.split(":")[0]), int(time_lower.split(":")[1])
                    ),
                    datetime.time(
                        int(time_upper.split(":")[0]), int(time_upper.split(":")[1])
                    ),
                ]
                self._time_info = (time_info[0], time_info[1])
            except Exception:
                raise RuntimeError("error processing time limit definition")
        self._days = cast(
            List[int],
            self.get_config_option(
                "days",
                required_type="[int]",
                allowed_values=list(range(0, 7)),
                default=list(range(0, 7)),
            ),
        )
        self._delay_notification = self.get_config_option(
            "delay", required_type="bool", default=False
        )
        self._dry_run = self.get_config_option(
            "dry_run", required_type="bool", default=False
        )
        self._ooh_recovery = self.get_config_option(
            "ooh_recovery", required_type="bool", default=False
        )

        if self.get_config_option("debug_times", required_type=bool, default=False):
            self._time_info = (
                (datetime.datetime.utcnow() - datetime.timedelta(minutes=1)).time(),
                (datetime.datetime.utcnow() + datetime.timedelta(minutes=1)).time(),
            )
            self.alerter_logger.debug("set times for alerter to %s", self._time_info)

        self._only_failures = self.get_config_option(
            "only_failures", required_type=bool, default=False
        )

        if self._ooh_failures is None:
            self._ooh_failures = []

    def get_config_option(
        self, key: str, **kwargs: Any
    ) -> Union[None, str, int, float, bool, List[str], List[int]]:
        kwargs["exception"] = AlerterConfigurationError
        return get_config_option(self._config_options, key, **kwargs)

    @property
    def dependencies(self) -> List[str]:
        """The Monitors we depend on.
        If a monitor we depend on fails, it means we can't reach the database, so we shouldn't bother trying to write to it."""
        return self._dependencies

    @dependencies.setter
    def dependencies(self, dependency_list: List[str]) -> None:
        if not isinstance(dependency_list, list):
            raise TypeError("dependency_list must be a list")
        self._dependencies = dependency_list

    @property
    def groups(self) -> List[str]:
        """The groups for which we alert"""
        retval = cast(List[str], self._groups)
        return retval

    @groups.setter
    def groups(self, group_list: List[str]) -> None:
        if not isinstance(group_list, list):
            raise TypeError("group_list must be a list")
        self._groups = group_list

    def check_dependencies(self, failed_list: List[str]) -> bool:
        """Check if anything we depend on has failed."""
        for dependency in failed_list:
            if dependency in self._dependencies:
                self.available = False
                return False
        self.available = True
        return True

    def should_alert(self, monitor: Monitor) -> AlertType:
        """Check if we should bother alerting, and what type."""
        out_of_hours = False

        if not self.available:
            return AlertType.NONE

        if not self._allowed_today():
            out_of_hours = True

        if not self._allowed_time():
            out_of_hours = True

        virtual_failure_count = monitor.virtual_fail_count()

        if virtual_failure_count:
            self.alerter_logger.debug("monitor %s has failed", monitor.name)
            # Monitor has failed (not just first time)
            if self._delay_notification:
                # Delayed notifications are enabled
                if not out_of_hours:
                    # Not out of hours
                    if self._ooh_failures is not None:
                        try:
                            self._ooh_failures.remove(monitor.name)
                            # if it was in there and we support catchup alerts, do it
                            if self.support_catchup:
                                return AlertType.CATCHUP
                        except ValueError:
                            pass
                        return AlertType.FAILURE
            # Delayed notifications are not enabled
            if virtual_failure_count == self._limit or (
                self._repeat and (virtual_failure_count % self._limit == 0)
            ):
                # This is the first time or nth time we've failed
                if out_of_hours:
                    if (
                        self._ooh_failures is not None
                        and monitor.name not in self._ooh_failures
                    ):
                        self._ooh_failures.append(monitor.name)
                        return AlertType.NONE
                return AlertType.FAILURE
            return AlertType.NONE

        # Not failed
        if (
            monitor.all_better_now()
            and monitor.last_virtual_fail_count() >= self._limit
        ):
            # was failed, and enough to have alerted
            try:
                if self._ooh_failures is not None:
                    self._ooh_failures.remove(monitor.name)
            except ValueError:
                pass
            if out_of_hours:
                if self._ooh_recovery and not self._only_failures:
                    return AlertType.SUCCESS
                return AlertType.NONE
            if not self._only_failures:
                return AlertType.SUCCESS
        return AlertType.NONE

    def send_alert(self, name: str, monitor: Any) -> Union[None, NoReturn]:
        """Abstract function to do the alerting."""
        raise NotImplementedError

    def _allowed_today(self) -> bool:
        """Check if today is an allowed day for an alert."""
        if arrow.now().weekday() not in self._days:
            self.alerter_logger.debug("not allowed to alert today")
            return False
        return True

    def _allowed_time(self) -> bool:
        """Check if now is an allowed time for an alert."""
        if self._times_type == AlertTimeFilter.ALWAYS:
            return True
        if self._time_info[0] is not None and self._time_info[1] is not None:
            now = arrow.now().time()
            in_time_range = (now > self._time_info[0]) and (now < self._time_info[1])
            if self._times_type == AlertTimeFilter.ONLY:
                self.alerter_logger.debug("in_time_range: {}".format(in_time_range))
                return in_time_range
            elif self._times_type == AlertTimeFilter.NOT:
                self.alerter_logger.debug(
                    "in_time_range: {} (inverting due to AlertTimeFilter.NOT)".format(
                        in_time_range
                    )
                )
                return not in_time_range
        self.alerter_logger.error(
            "this should never happen! Unknown times_type in alerter"
        )
        return True

    @staticmethod
    def _get_verb(alert_type: AlertType) -> str:
        if alert_type == AlertType.CATCHUP:
            return "failed earlier"
        elif alert_type == AlertType.FAILURE:
            return "failed"
        elif alert_type == AlertType.SUCCESS:
            return "succeeded"
        else:
            return "unknowned"

    @staticmethod
    def build_message(
        length: AlertLength, alert_type: AlertType, monitor: Monitor
    ) -> str:
        if monitor._state == MonitorState.FAILED:
            downtime = str(monitor.get_downtime())
        elif monitor._state == MonitorState.OK:
            downtime = str(monitor.get_uptime())
        else:
            downtime = ""

        max_length = None  # type: Optional[int]
        if length == AlertLength.NOTIFICATION:
            message = "Monitor {monitor.name} {alert_verb}".format(
                monitor=monitor, alert_verb=Alerter._get_verb(alert_type)
            )
        elif length in [AlertLength.SMS, AlertLength.ONELINE]:
            message = "{alert_type}: {monitor.name} {alert_verb} on {monitor.running_on} at {failure_time} ({downtime}): {result}".format(
                alert_type=alert_type.value,
                alert_verb=Alerter._get_verb(alert_type),
                downtime=downtime,
                failure_time=format_datetime(monitor.first_failure_time()),
                monitor=monitor,
                result=monitor.get_result(),
            )
            if length == AlertLength.SMS:
                max_length = 160
        elif length == AlertLength.TERSE:
            raise NotImplementedError
        elif length == AlertLength.FULL:
            if alert_type in [AlertType.CATCHUP, AlertType.FAILURE]:
                message = """
                Monitor {monitor.name}{host} {alert_verb}!
                Failed at: {failure_time} (down {downtime})
                Virtual failure count: {vfc}
                Additional info: {result}
                Description: {desc}
                """
                if monitor.recover_info != "":
                    message = message + "Recovery info: {}\n".format(
                        monitor.recover_info
                    )
                if monitor.failure_doc:
                    message = message + "Documentation: {}\n".format(
                        monitor.failure_doc
                    )
            elif alert_type == AlertType.SUCCESS:
                message = """
                Monitor {monitor.name}{host} {alert_verb}!
                Recovered at: {recovered_time}
                Additional info: {result}
                Description: {desc}
                """
                if monitor.recovered_info != "":
                    message = message + "Recovery info: {}".format(
                        monitor.recovered_info
                    )
            else:
                raise ValueError(
                    "Can't write a message for AlertType {}".format(alert_type)
                )
            if monitor.is_remote:
                host = " on {}".format(monitor.running_on)
            else:
                host = ""
            message = message.format(
                alert_type=alert_type,
                monitor=monitor,
                alert_verb=Alerter._get_verb(alert_type),
                failure_time=format_datetime(monitor.first_failure_time()),
                downtime=downtime,
                result=monitor.get_result(),
                host=host,
                desc=monitor.describe(),
                vfc=monitor.virtual_fail_count(),
                recovered_time=format_datetime(monitor.last_update),
            )
            message = textwrap.dedent(message)
        else:
            raise NotImplementedError
        if max_length and len(message) > max_length:
            message = textwrap.shorten(message, width=max_length, placeholder="...")
        return message

    @property
    def type(self) -> str:
        """Compatibility with the rename of type to _type. Will be removed in the future."""
        self.alerter_logger.critical("Access to 'type' instead of '_type'!")
        return self._type


(register, get_class, all_types) = subclass_dict_handler(
    "simplemonitor.Alerters.alerter", Alerter
)
