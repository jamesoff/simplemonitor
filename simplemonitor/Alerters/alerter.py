# coding=utf-8
"""
Alerting for SimpleMonitor
"""

import datetime
import logging
import os
import textwrap
from enum import Enum
from socket import gethostname
from typing import Any, List, NoReturn, Optional, Tuple, Union, cast

import arrow

from ..Monitors.monitor import Monitor
from ..util import (
    MonitorState,
    check_group_match,
    format_datetime,
    get_config_option,
    short_hostname,
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

    alerter_type = "unknown"
    _dependencies = None  # type: Optional[List[str]]
    hostname = gethostname()

    name = None  # type: Optional[str]

    _ooh_failures = None  # type: Optional[List[str]]
    # subclasses should set this to true if they support catchup notifications for delays
    support_catchup = False
    urgent = False

    def __init__(self, config_options: Optional[dict] = None) -> None:
        if config_options is None:
            config_options = {}
        self._config_options = config_options
        self.alerter_logger = logging.getLogger(
            "simplemonitor.alerter-" + self.alerter_type
        )
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
                time_lower_split = list(map(int, time_lower.split(":")))
                time_upper_split = list(map(int, time_upper.split(":")))
                time_info = [
                    datetime.time(time_lower_split[0], time_lower_split[1]),
                    datetime.time(time_upper_split[0], time_upper_split[1]),
                ]
                self._time_info = (time_info[0], time_info[1])
            except Exception as error:
                raise RuntimeError("error processing time limit definition") from error
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

        if self.get_config_option("debug_times", required_type="bool", default=False):
            self._time_info = (
                (datetime.datetime.utcnow() - datetime.timedelta(minutes=1)).time(),
                (datetime.datetime.utcnow() + datetime.timedelta(minutes=1)).time(),
            )
            self.alerter_logger.debug("set times for alerter to %s", self._time_info)

        self._only_failures = self.get_config_option(
            "only_failures", required_type="bool", default=False
        )
        self._tz = cast(
            str, self.get_config_option("tz", default=os.environ.get("TZ", "UTC"))
        )
        self._times_tz = cast(
            str,
            self.get_config_option("times_tz", default=os.environ.get("TZ", "local")),
        )
        self.urgent = cast(
            bool,
            self.get_config_option("urgent", default=self.urgent, required_type="bool"),
        )

        if self._ooh_failures is None:
            self._ooh_failures = []

    def get_config_option(
        self,
        key: str,
        *,
        default: Any = None,
        required: bool = False,
        required_type: str = "str",
        allowed_values: Any = None,
        allow_empty: bool = True,
        minimum: Optional[Union[int, float]] = None,
        maximum: Optional[Union[int, float]] = None,
    ) -> Any:
        """Get a config value.

        Throws the right flavour exception if something is wrong."""
        return get_config_option(
            self._config_options,
            key,
            default=default,
            required=required,
            required_type=required_type,
            allowed_values=allowed_values,
            allow_empty=allow_empty,
            minimum=minimum,
            maximum=maximum,
        )

    @property
    def dependencies(self) -> List[str]:
        """The Monitors we depend on.

        If a monitor we depend on fails, it means we can't reach the database,
        so we shouldn't bother trying to write to it."""
        if self._dependencies is not None:
            return self._dependencies
        return []

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
        if self._dependencies is None or len(self._dependencies) == 0:
            return True
        for dependency in failed_list:
            if dependency in self._dependencies:
                return False
        return True

    def should_alert(self, monitor: Monitor) -> AlertType:
        """Check if we should bother alerting, and what type."""
        out_of_hours = False

        if not check_group_match(monitor.group, self.groups):
            self.alerter_logger.debug(
                "not alerting for %s: group mismatch (monitor: %s; alerter: %s)",
                monitor.name,
                monitor.group,
                self.groups,
            )
            return AlertType.NONE

        # Sanity check
        if not monitor.enabled:
            self.alerter_logger.debug(
                "not alerting for %s: monitor disabled", monitor.name
            )
            return AlertType.NONE

        if self.urgent and not monitor.urgent:
            self.alerter_logger.debug(
                "not alerting for %s: alerter is urgent and monitor is not",
                monitor.name,
            )
            return AlertType.NONE

        if not self._allowed_today():
            out_of_hours = True

        if not self._allowed_time():
            out_of_hours = True

        # ensure OOH list is initalised to the empty list if not done
        if self._ooh_failures is None:
            self._ooh_failures = []

        virtual_failure_count = monitor.virtual_fail_count()

        if virtual_failure_count:
            self.alerter_logger.debug("monitor %s has failed", monitor.name)
            # Monitor has failed (not just first time)
            if self._delay_notification:
                # Delayed (catch-up) notifications are enabled
                if not out_of_hours:
                    # Not out of hours
                    try:
                        self._ooh_failures.remove(monitor.name)
                        # if it was in there and we support catchup alerts, do it
                        if self.support_catchup:
                            self.alerter_logger.debug(
                                "alert for monitor %s is CATCHUP", monitor.name
                            )
                            return AlertType.CATCHUP
                    except ValueError:
                        pass
                    self.alerter_logger.debug(
                        "alert for monitor %s is FAILURE", monitor.name
                    )
                    return AlertType.FAILURE
            # Delayed notifications are not enabled (or are, and we didn't do anything above)
            if virtual_failure_count == self._limit or (
                self._repeat and (virtual_failure_count % self._limit == 0)
            ):
                # This is the first time or nth time we've failed
                if out_of_hours:
                    if monitor.name not in self._ooh_failures:
                        self._ooh_failures.append(monitor.name)
                    self.alerter_logger.debug("not alerting for %s: OOH", monitor.name)
                    return AlertType.NONE
                self.alerter_logger.debug(
                    "alert for monitor %s is FAILURE", monitor.name
                )
                return AlertType.FAILURE
            self.alerter_logger.debug(
                "not alerting for monitor %s: not failed or repeated enough",
                monitor.name,
            )
            return AlertType.NONE

        # Not failed
        if (
            monitor.all_better_now()
            and monitor.last_virtual_fail_count() >= self._limit
        ):
            # was failed, and enough to have alerted
            self.alerter_logger.debug("monitor %s has recovered", monitor.name)
            try:
                self._ooh_failures.remove(monitor.name)
            except ValueError:
                pass
            if out_of_hours:
                if self._ooh_recovery and not self._only_failures:
                    self.alerter_logger.debug(
                        "alert for monitor %s is SUCCESS (OOH recovery)", monitor.name
                    )
                    return AlertType.SUCCESS
                self.alerter_logger.debug(
                    "not alerting for monitor %s: OOH and not recovery/only failures",
                    monitor.name,
                )
                return AlertType.NONE
            if not self._only_failures:
                self.alerter_logger.debug(
                    "alert for monitor %s is SUCCESS", monitor.name
                )
                return AlertType.SUCCESS
        return AlertType.NONE

    def send_alert(self, name: str, monitor: Any) -> Union[None, NoReturn]:
        """Abstract function to do the alerting."""
        raise NotImplementedError

    def _allowed_today(self) -> bool:
        """Check if today is an allowed day for an alert."""
        if arrow.now(self._times_tz).weekday() not in self._days:
            self.alerter_logger.debug("not allowed to alert today")
            return False
        return True

    def _allowed_time(self) -> bool:
        """Check if now is an allowed time for an alert."""
        if self._times_type == AlertTimeFilter.ALWAYS:
            return True
        if self._time_info[0] is not None and self._time_info[1] is not None:
            now = arrow.now(self._times_tz).time()
            in_time_range = self._time_info[0] <= now < self._time_info[1]
            if self._times_type == AlertTimeFilter.ONLY:
                self.alerter_logger.debug("in_time_range: %s", in_time_range)
                return in_time_range
            if self._times_type == AlertTimeFilter.NOT:
                self.alerter_logger.debug(
                    "in_time_range: %s (inverting due to AlertTimeFilter.NOT)",
                    in_time_range,
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
        if alert_type == AlertType.FAILURE:
            return "failed"
        if alert_type == AlertType.SUCCESS:
            return "succeeded"
        return "unknowned"

    def build_message(
        self, length: AlertLength, alert_type: AlertType, monitor: Monitor
    ) -> str:
        """Create a message for an Alerter to send."""
        if monitor.state() == MonitorState.FAILED:
            downtime = str(monitor.get_downtime())
        elif monitor.state() == MonitorState.OK:
            downtime = str(monitor.get_wasdowntime())
        else:
            downtime = ""

        host = " on {}".format(
            monitor.running_on if monitor.is_remote() else self.hostname
        )

        max_length = None  # type: Optional[int]
        if length == AlertLength.NOTIFICATION:
            message = "Monitor {monitor.name}{host} {alert_verb}".format(
                monitor=monitor,
                alert_verb=Alerter._get_verb(alert_type),
                host=host,
            )
        elif length in [AlertLength.SMS, AlertLength.ONELINE]:
            host = " on {}".format(
                monitor.running_on if monitor.is_remote() else short_hostname()
            )
            message = (
                "{alert_type}: {monitor.name}{host} {alert_verb} "
                "at {failure_time} ({downtime}): {result}"
            ).format(
                alert_type=alert_type.value,
                alert_verb=Alerter._get_verb(alert_type),
                downtime=downtime,
                failure_time=format_datetime(monitor.first_failure_time(), self._tz),
                monitor=monitor,
                host=host,
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
                Recovered at: {recovered_time} (was down for {downtime})
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
            message = message.format(
                alert_type=alert_type,
                monitor=monitor,
                alert_verb=Alerter._get_verb(alert_type),
                failure_time=format_datetime(monitor.first_failure_time(), self._tz),
                downtime=downtime,
                result=monitor.get_result(),
                host=host,
                desc=monitor.describe(),
                vfc=monitor.virtual_fail_count(),
                recovered_time=format_datetime(monitor.last_update, self._tz),
            )
            message = textwrap.dedent(message)
        else:
            raise NotImplementedError
        if max_length and len(message) > max_length:
            message = textwrap.shorten(message, width=max_length, placeholder="...")
        return message

    def _describe_times(self) -> str:
        """Return a string describing the times we're active."""
        if self._times_type == AlertTimeFilter.ALWAYS:
            return "(always)"
        days_list = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        if self._days != list(range(0, 7)):
            allowed_days = ", ".join([days_list[day] for day in sorted(self._days)])
        else:
            allowed_days = "any day"
        start, end = self._time_info
        if start is None or end is None:
            return "(misconfigured times)"
        message = "between {start} and {end} ({tz}) on {days}".format(
            start=start.strftime("%H:%M"),
            end=end.strftime("%H:%M"),
            days=allowed_days,
            tz=self._times_tz,
        )
        if self._times_type == AlertTimeFilter.ONLY:
            return "only {}".format(message)
        return "any time except {}".format(message)

    def _describe_action(self) -> str:
        """Return a string explaining what we do.

        Should not include any time info"""
        raise NotImplementedError

    def describe(self) -> str:
        """Return a string explaining what we do."""
        return "{desc} {when}".format(
            desc=self._describe_action(), when=self._describe_times()
        )


(register, get_class, all_types) = subclass_dict_handler(
    "simplemonitor.Alerters.alerter", Alerter, "alerter_type"
)
