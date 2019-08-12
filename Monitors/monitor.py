# coding=utf-8
"""A collection of monitors for the SimpleMonitor application.

The Monitor class contains the monitor-independent logic for handling results etc.

Subclasses should provide an __init__(), and override at least run_test() to actually
perform the test. A successful test should call self.record_success() and a failed one
should call self.record_fail(). You should also override the describe() and get_params()
functions.

"""

import platform
import sys
import datetime
import time
import copy
import subprocess
import logging

try:
    import win32api  # noqa: F401

    win32_available = True
except ImportError:
    win32_available = False

from util import get_config_option, MonitorConfigurationError, short_hostname
from util import subclass_dict_handler


class Monitor:
    """Simple monitor. This class is abstract."""

    type = "unknown"
    last_result = ""
    error_count = 0
    failed_at = None
    success_count = 0
    tests_run = 0
    last_error_count = 0
    last_run_duration = 0

    failures = 0
    last_failure = None

    # this is the time we last received data into this monitor (if we're remote)
    last_update = None

    def __init__(self, name="unnamed", config_options=None):
        """What's that coming over the hill? Is a monitor?"""
        if config_options is None:
            config_options = {}
        self.name = name
        self.deps = []
        self.monitor_logger = logging.getLogger("simplemonitor.monitor-" + self.name)
        self._dependencies = Monitor.get_config_option(
            config_options, "depend", required_type="[str]", default=list()
        )
        self._urgent = Monitor.get_config_option(
            config_options, "urgent", required_type="bool", default=True
        )
        self._notify = Monitor.get_config_option(
            config_options, "notify", required_type="bool", default=True
        )
        self.group = Monitor.get_config_option(
            config_options, "group", default="default"
        )
        self._tolerance = Monitor.get_config_option(
            config_options, "tolerance", required_type="int", default=0, minimum=0
        )
        self.remote_alerting = Monitor.get_config_option(
            config_options, "remote_alert", required_type="bool", default=False
        )
        self._recover_command = Monitor.get_config_option(
            config_options, "recover_command"
        )
        self.recover_info = ""
        self.minimum_gap = Monitor.get_config_option(
            config_options, "gap", required_type="int", minimum=0, default=0
        )

        self.running_on = short_hostname()
        self.was_skipped = False
        self._last_run = 0

    @staticmethod
    def get_config_option(config_options, key, **kwargs):
        kwargs["exception"] = MonitorConfigurationError
        return get_config_option(config_options, key, **kwargs)

    @property
    def dependencies(self):
        """The Monitors we depend on.
        If a monitor we depend on fails, we will skip"""
        return self._dependencies

    @dependencies.setter
    def dependencies(self, dependency_list):
        if not isinstance(dependency_list, list):
            raise TypeError("dependency_list must be a list")
        self._dependencies = dependency_list

    def is_remote(self):
        """Check if we're running on this machine, or if we're a remote instance."""
        if self.running_on == short_hostname():
            return False
        return True

    def run_test(self):
        """Override this method to perform the test."""
        raise NotImplementedError

    def virtual_fail_count(self):
        """Return the number of failures we've had past our tolerance."""
        vfs = self.error_count - self._tolerance
        if vfs < 0:
            vfs = 0
        return vfs

    def test_success(self):
        """Returns false if the test has failed."""
        if self.error_count > self._tolerance:
            return False
        else:
            return True

    def first_failure(self):
        """Check if this is our first failure (past tolerance)."""
        if self.error_count == (self._tolerance + 1):
            return True
        else:
            return False

    def state(self):
        """Returns false if the last test failed."""
        if self.error_count > 0:
            return False
        else:
            return True

    def get_result(self):
        """Return the result info from the last test."""
        return self.last_result

    def reset_dependencies(self):
        """Reset the monitor's dependency list back to default."""
        self.deps = copy.copy(self._dependencies)

    def dependency_succeeded(self, dependency):
        """Remove a dependency from the current version of the list."""
        try:
            self.deps.remove(dependency)
        except Exception:
            pass

    def get_dependencies(self):
        """Return our outstanding dependencies."""
        return self.deps

    def set_dependencies(self, dependencies):
        """Set our master list of dependencies."""
        self._dependencies = dependencies
        self.reset_dependencies()

    def log_result(self, name, logger):
        """Save our latest result to the logger.

        To be removed."""
        if self.error_count > self._tolerance:
            result = 0
        else:
            result = 1
        try:
            logger.save_result2(name, self)
        except Exception as e:
            sys.stderr.write("%s\n" % e)
            logger.save_result(
                name, self.type, self.get_params(), result, self.last_result
            )

    def send_alert(self, name, alerter):
        """Send an alert when we first fail.

        Set first_only to False to generate mail every time.

        To be removed."""

        if self.virtual_fail_count() == 1:
            alerter.send_alert(name, self)

    def get_params(self):
        """Override this method to return a list of parameters (for logging)"""
        raise NotImplementedError

    def set_mon_refs(self, mmm):
        """Called with a reference to the list of all monitors.
        Only used by CompoundMonitor for now."""
        pass

    @property
    def minimum_gap(self):
        """Minimum gap between runs of the monitor."""
        return self._minimum_gap

    @minimum_gap.setter
    def minimum_gap(self, gap):
        if isinstance(gap, int):
            if gap < 0:
                raise ValueError("gap must be at least 0")
            self._minimum_gap = int(gap)
        else:
            raise TypeError("gap must be an integer")

    def describe(self):
        """Explain what this monitor does.
        We don't throw NotImplementedError here as it won't show up until something breaks,
        and we don't want to randomly die then."""
        return "(Monitor did not write an auto-biography.)"

    def is_windows(self, allow_cygwin=True):
        """Checks if our platform is Windowsy.
        If allow_cygwin is False, cygwin will be reported as UNIX."""

        platforms = ["Microsoft", "Windows"]
        if allow_cygwin:
            platforms.append("CYGWIN_NT-6.0")

        if platform.system() in platforms:
            return True
        else:
            return False

    def record_fail(self, message=""):
        """Update internal state to show that we had a failure."""
        self.error_count += 1
        self.last_update = datetime.datetime.utcnow()
        self.last_result = str(message)
        if self.virtual_fail_count() == 1:
            self.failed_at = datetime.datetime.utcnow()
            self.last_failure = datetime.datetime.utcnow()
            self.failures += 1
        self.success_count = 0
        self.tests_run += 1
        self.was_skipped = False
        return False

    def record_success(self, message=""):
        """Update internal state to show we had a success."""
        if self.error_count > 0:
            self.last_error_count = self.error_count
        self.error_count = 0
        self.last_update = datetime.datetime.utcnow()
        self.last_result = ""
        self.success_count += 1
        self.tests_run += 1
        self.was_skipped = False
        self.last_result = message
        return True

    def record_skip(self, which_dep):
        """Record that we were skipped.

        We pretend to have succeeded as we don't want notifications sent."""
        if which_dep is not None:
            # we were skipped because of a dependency
            self.record_success()
            self.was_skipped = True
            self.skip_dep = which_dep
        else:
            # we were skipped because of the gap value
            self.was_skipped = True
        return True

    def skipped(self):
        if self.was_skipped:
            return True
        else:
            return False

    def get_success_count(self):
        """Get the number of successful tests."""
        if self.tests_run == 0:
            return 0
        return self.success_count

    def all_better_now(self):
        """Check if we've just recovered."""
        try:
            if self.just_recovered:
                return True
        except Exception:
            pass

        if (
            self.last_error_count >= self._tolerance
            and self.success_count == 1
            and not self.was_skipped
        ):
            return True
        else:
            return False

    def first_failure_time(self):
        """Get a datetime object showing when we first failed."""
        return self.failed_at

    def get_error_count(self):
        """Get the number of times we've failed (ignoring tolerance)."""
        return self.error_count

    @property
    def notify(self):
        return self._notify

    @notify.setter
    def notify(self, value):
        if isinstance(value, bool):
            self._notify = value
        else:
            raise TypeError("notify must be a bool")

    @property
    def urgent(self):
        return self._urgent

    @urgent.setter
    def urgent(self, value):
        if isinstance(value, bool):
            self._urgent = value
        elif isinstance(value, int):
            if value:
                self._urgent = True
            else:
                self._urgent = False
        else:
            raise TypeError("urgent should be a bool, or an int at a push")

    def set_notify(self, notify):
        """Record if this monitor needs notifications."""
        self.notify = notify

    def should_run(self):
        """Check if we should run our tests.

        We always run if the minimum gap is 0, or if we're currently failing.
        Otherwise, we run if the last time we ran was more than minimum_gap seconds ago.
        """
        now = int(time.time())
        if self.minimum_gap == 0:
            self._last_run = now
            return True
        if self.error_count > 0:
            self._last_run = now
            return True
        if self._last_run == 0:
            self._last_run = now
            return True
        gap = now - self._last_run
        if gap >= self.minimum_gap:
            self._last_run = now
            return True
        return False

    def last_virtual_fail_count(self):
        if (self.last_error_count - self._tolerance) < 0:
            return 0
        else:
            return self.last_error_count - self._tolerance

    def attempt_recover(self):
        if self._recover_command is None:
            self.recover_info = ""
            return
        if not self.first_failure():
            return

        try:
            p = subprocess.Popen(self._recover_command.split(" "))
            p.wait()
            self.recover_info = "Command executed and returned %d" % p.returncode
        except Exception as e:
            self.recover_info = "Unable to run command: %s" % e

        return

    def post_config_setup(self):
        """ any post config setup needed """
        pass

    def __getstate__(self):
        """Loggers (the Python kind, not the SimpleMonitor kind) can't be serialized.
        In order to work around that, we omit them when getting serialized (for
        being sent over the network).
        """
        serialize_dict = dict(self.__dict__)
        del serialize_dict["monitor_logger"]
        return serialize_dict

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._set_monitor_logger()

    def _set_monitor_logger(self):
        self.monitor_logger = logging.getLogger("simplemonitor.monitor-" + self.name)

    def to_python_dict(self):
        return self.__getstate__()

    @classmethod
    def from_python_dict(cls, d):
        monitor = Monitor()
        monitor.__class__ = cls
        monitor.__setstate__(d)
        return monitor

    def get_downtime(self):
        try:
            downtime = datetime.datetime.utcnow() - self.first_failure_time()
            downtime_seconds = downtime.seconds
            (hours, minutes) = (0, 0)
            if downtime_seconds > 3600:
                (hours, downtime_seconds) = divmod(downtime_seconds, 3600)
            if downtime_seconds > 60:
                (minutes, downtime_seconds) = divmod(downtime_seconds, 60)
            return (downtime.days, hours, minutes, downtime_seconds)
        except TypeError:
            return (0, 0, 0, 0)

    def __str__(self):
        return self.describe()


(register, get_class, all_types) = subclass_dict_handler(
    "simplemonitor.Monitors.monitor", Monitor
)


@register
class MonitorFail(Monitor):
    """A monitor which always fails.

    Use for testing alerters etc."""

    type = "fail"

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        self.interval = Monitor.get_config_option(
            config_options, "interval", required_type="int", minimum=1, default=5
        )

    def run_test(self):
        """Always fails."""
        self.monitor_logger.info(
            "error_count = %d, interval = %d --> %d",
            self.error_count,
            self.interval,
            self.error_count % self.interval,
        )
        if (
            (self.interval == 0)
            or (self.error_count == 0)
            or (self.error_count % self.interval != 0)
        ):
            self.record_fail("This monitor always fails.")
            return False
        else:
            self.record_success()
            return True

    def describe(self):
        return "A monitor which always fails."

    def get_params(self):
        return (self.interval,)


@register
class MonitorNull(Monitor):
    """A monitor which always passes."""

    type = "null"

    def run_test(self):
        self.record_success()

    def get_params(self):
        return ()
