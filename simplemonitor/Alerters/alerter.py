# coding=utf-8
"""Alerting for SimpleMonitor"""

import datetime
import logging
from enum import Enum
from socket import gethostname
from typing import Any, List, NoReturn, Optional, Tuple, Union, cast

from ..Monitors.monitor import Monitor
from ..util import AlerterConfigurationError, get_config_option, subclass_dict_handler


class AlertType(Enum):
    """What type of alert should be sent"""

    NONE = 0
    FAILURE = 1
    CATCHUP = 2
    SUCCESS = 3


class AlertTimeFilter(Enum):
    """How should the Alerter times be handled"""

    ALWAYS = 0  # specified times are meaningless
    NOT = 1  # not allowed between the specified times
    ONLY = 2  # only allowed between the specified times


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
        assert isinstance(self._groups, list)
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

        if not self.allowed_today():
            out_of_hours = True

        if not self.allowed_time():
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
                if self._ooh_recovery:
                    return AlertType.SUCCESS
                return AlertType.NONE
            return AlertType.SUCCESS
        return AlertType.NONE

    def send_alert(self, name: str, monitor: Any) -> Union[None, NoReturn]:
        """Abstract function to do the alerting."""
        raise NotImplementedError

    def allowed_today(self) -> bool:
        """Check if today is an allowed day for an alert."""
        if datetime.datetime.now().weekday() not in self._days:
            self.alerter_logger.debug("not allowed to alert today")
            return False
        return True

    def allowed_time(self) -> bool:
        """Check if now is an allowed time for an alert."""
        if self._times_type == AlertTimeFilter.ALWAYS:
            return True
        if self._time_info[0] is not None and self._time_info[1] is not None:
            now = datetime.datetime.now().time()
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

    @property
    def type(self) -> str:
        """Compatibility with the rename of type to _type. Will be removed in the future."""
        self.alerter_logger.critical("Access to 'type' instead of '_type'!")
        return self._type


(register, get_class, all_types) = subclass_dict_handler(
    "simplemonitor.Alerters.alerter", Alerter
)
