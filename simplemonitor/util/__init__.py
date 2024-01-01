"""Utilities for SimpleMonitor."""

import datetime
import os
import shutil
import socket
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import arrow

from .envconfig import EnvironmentAwareConfigParser


class MonitorConfigurationError(ValueError):
    """A config error for a Monitor"""


class AlerterConfigurationError(ValueError):
    """A config error for an Alerter"""


class LoggerConfigurationError(ValueError):
    """A config error for a Logger"""


class SimpleMonitorConfigurationError(ValueError):
    """A general config error"""


class MonitorState(Enum):
    """Represent the state of a Monitor."""

    UNKNOWN = 0  # state not known yet
    SKIPPED = 1  # monitor was skipped
    OK = 2  # monitor is ok
    FAILED = 3  # monitor has failed


class UpDownTime:
    """Represent an up- or downtime"""

    days = 0
    hours = 0
    minutes = 0
    seconds = 0

    def __init__(
        self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0
    ) -> None:
        if not isinstance(days, int):
            raise TypeError("days must be an int")
        if not isinstance(hours, int):
            raise TypeError("days must be an int")
        if not isinstance(minutes, int):
            raise TypeError("days must be an int")
        if not isinstance(seconds, int):
            raise TypeError("days must be an int")
        self.days = days
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds
        if self.seconds >= 60:
            temp_min, self.seconds = divmod(self.seconds, 60)
            self.minutes += temp_min
        if self.minutes >= 60:
            temp_hour, self.minutes = divmod(self.minutes, 60)
            self.hours += temp_hour
        if self.hours >= 24:
            temp_day, self.hours = divmod(self.hours, 24)
            self.days += temp_day

    def __str__(self) -> str:
        """Format as d+h:m:s"""
        return "{}+{:02}:{:02}:{:02}".format(
            self.days, self.hours, self.minutes, int(self.seconds)
        )

    def __repr__(self) -> str:
        return "<{}: {}>".format(self.__class__, self.__str__())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UpDownTime):
            return NotImplemented
        if (
            self.days == other.days
            and self.hours == other.hours
            and self.minutes == other.minutes
            and self.seconds == other.seconds
        ):
            return True
        return False

    @staticmethod
    def from_timedelta(td: datetime.timedelta) -> "UpDownTime":
        """Generate an UpDownTime from a timedelta object"""
        if td is None:
            return UpDownTime()
        downtime_seconds = td.seconds
        (hours, minutes) = (0, 0)
        if downtime_seconds > 3600:
            (hours, downtime_seconds) = divmod(downtime_seconds, 3600)
        if downtime_seconds > 60:
            (minutes, downtime_seconds) = divmod(downtime_seconds, 60)
        return UpDownTime(td.days, hours, minutes, downtime_seconds)


def get_config_option(
    config_options: Dict[str, Any],
    key: str,
    *,
    default: Any = None,
    required: bool = False,
    required_type: str = "str",
    allowed_values: Any = None,
    allow_empty: bool = True,
    minimum: Optional[Union[int, float]] = None,
    maximum: Optional[Union[int, float]] = None,
) -> Union[None, str, int, float, bool, List[str], List[int]]:
    """Get a value out of a dict, with possible default, required type and requiredness."""

    if not isinstance(config_options, dict):
        raise TypeError("config_options should be a dict")

    value = config_options.get(key, default)
    if required and value is None:
        raise ValueError(f"config option {key} is missing and is required")
    if isinstance(value, str) and required_type:
        if required_type == "str" and value == "" and not allow_empty:
            raise ValueError(f"config option {key} cannot be empty")
        if required_type in ["int", "float"]:
            try:
                if required_type == "int":
                    value = int(value)
                else:
                    value = float(value)
            except TypeError as error:
                raise TypeError(
                    f"config option {key} needs to be an {required_type}"
                ) from error
            if minimum is not None and value < minimum:
                raise ValueError(f"config option {key} needs to be >= {minimum}")
            if maximum is not None and value > maximum:
                raise ValueError(f"config option {key} needs to be <= {minimum}")
        if required_type == "[int]":
            if not isinstance(value, str):
                raise ValueError(
                    f"config option {key} needs to be a list of int,int,..."
                )
            try:
                value = [int(x) for x in value.split(",")]
            except ValueError as error:
                raise ValueError(
                    f"config option {key} needs to be a list of int[int,...]"
                ) from error
        if required_type == "bool":
            value = bool(str(value).lower() in ["1", "true", "yes"])
        if required_type == "[str]":
            if not isinstance(value, str):
                raise ValueError(
                    f"config option {key} needs to be a list of int,int,..."
                )
            value = [x.strip() for x in value.split(",")]
    if isinstance(value, list) and allowed_values:
        if not all(x in allowed_values for x in value):
            raise ValueError(f"config option {key} needs to be one of {allowed_values}")
    else:
        if allowed_values is not None and value not in allowed_values:
            raise ValueError(f"config option {key} needs to be one of {allowed_values}")
    return value


def format_datetime(
    the_datetime: Optional[Union[arrow.Arrow, datetime.datetime]],
    tz: Optional[str] = None,
) -> str:
    """Return an isoformat()-like datetime without the microseconds."""
    if the_datetime is None:
        retval = ""
    elif isinstance(the_datetime, (arrow.Arrow, datetime.datetime)):
        the_datetime = the_datetime.replace(microsecond=0)
        retval = the_datetime.isoformat(" ")
        if isinstance(the_datetime, arrow.Arrow):
            if tz is not None:
                retval = the_datetime.to(tz).isoformat(" ")
    else:
        retval = str(the_datetime)
    return retval


def short_hostname() -> str:
    """Get just our machine name.

    TODO: This might actually be redundant. Python probably provides it's own version of this.
    """

    return (socket.gethostname() + ".").split(".")[0]


def get_config_dict(
    config: EnvironmentAwareConfigParser, monitor: str
) -> Dict[str, str]:
    options = config.items(monitor)
    ret = {}
    for key, value in options:
        ret[key] = value
    return ret


def subclass_dict_handler(
    mod: str, base_cls: type, type_attr: str
) -> Tuple[Callable, Callable, Callable]:
    def _check_is_subclass(cls: Any) -> None:
        if not issubclass(cls, base_cls):
            raise TypeError(
                ("%s.register may only be used on subclasses " "of %s.%s")
                % (mod, mod, base_cls.__name__)
            )

    _subclasses = {}

    def register(cls: Any) -> Any:
        """Decorator for monitor classes."""
        _check_is_subclass(cls)
        if cls is None or getattr(cls, type_attr, "unknown") == "unknown":
            raise ValueError("Cannot register this class")
        _subclasses[getattr(cls, type_attr)] = cls
        return cls

    def get_class(type_: Any) -> Any:
        return _subclasses[type_]

    def all_types() -> list:
        return list(_subclasses)

    return (register, get_class, all_types)


def check_group_match(group: str, group_list: List[str]) -> bool:
    """
    Check if a group is contained in the group list.

    If the group list is a single element, "_all", then it matches.
    """
    if group_list[0] == "_all":
        return True
    if group in group_list:
        return True
    return False


def size_string_to_bytes(s: str) -> Optional[int]:
    if s is None:
        return None
    if s.endswith("G"):
        gigs = int(s[:-1])
        _bytes = gigs * (1024**3)
    elif s.endswith("M"):
        megs = int(s[:-1])
        _bytes = megs * (1024**2)
    elif s.endswith("K"):
        kilos = int(s[:-1])
        _bytes = kilos * 1024
    else:
        return int(s)
    return _bytes


def bytes_to_size_string(b: int) -> str:
    """Convert a number in bytes to a sensible unit."""

    kb = 1024
    mb = kb * 1024
    gb = mb * 1024
    tb = gb * 1024

    if b > tb:
        return "%0.2fTiB" % (b / float(tb))
    if b > gb:
        return "%0.2fGiB" % (b / float(gb))
    if b > mb:
        return "%0.2fMiB" % (b / float(mb))
    if b > kb:
        return "%0.2fKiB" % (b / float(kb))
    return str(b)


def copy_if_different(source: str, dest: str) -> bool:
    """Copy a file from src to dest, if newer or a different size"""
    do_copy = False
    if not os.path.exists(source):
        return False
    if os.path.isdir(dest):
        dest = os.path.join(dest, os.path.basename(source))
    if not os.path.exists(dest):
        do_copy = True
    else:
        source_fileinfo = os.stat(source)
        dest_fileinfo = os.stat(dest)
        if source_fileinfo.st_size != dest_fileinfo.st_size:
            do_copy = True
        elif source_fileinfo.st_mtime > dest_fileinfo.st_mtime:
            do_copy = True
    if not do_copy:
        return False
    try:
        shutil.copy(source, dest)
    except IOError:
        return False
    return True
