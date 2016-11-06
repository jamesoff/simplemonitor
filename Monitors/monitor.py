
"""A collection of monitors for the SimpleMonitor application.

The Monitor class contains the monitor-independent logic for handling results etc.

Subclasses should provide an __init__(), and override at least run_test() to actually
perform the test. A successful test should call self.record_success() and a failed one
should call self.record_fail(). You should also override the describe() and get_params()
functions.

"""

import socket
import platform
import sys
import datetime
import time
import copy
import subprocess

try:
    import win32api
    win32_available = True
except:
    win32_available = False


class Monitor:
    """Simple monitor. This class is abstract."""

    last_result = ""
    type = "unknown"
    error_count = 0
    tolerance = 0
    failed_at = None
    success_count = 0
    tests_run = 0
    last_error_count = 0
    last_run_duration = 0

    minimum_gap = 0
    last_run = 0

    urgent = 1

    failures = 0
    last_failure = None

    # this is the time we last received data into this monitor (if we're remote)
    last_update = None

    # we set this to true if we want a remote instance to do our alerts for us
    remote_alerting = False

    # dependencies holds master list
    _dependencies = []

    # deps holds temporary list
    deps = []

    name = "unnamed"

    recover_command = ""
    recover_info = ""

    def __init__(self, name="unnamed", config_options={}):
        """What's that coming over the hill? Is a monitor?"""
        if 'depend' in config_options:
            self.set_dependencies([x.strip() for x in config_options["depend"].split(",")])
        if 'urgent' in config_options:
            self.set_urgency(int(config_options["urgent"]))
        if 'tolerance' in config_options:
            self.set_tolerance(int(config_options["tolerance"]))
        if 'remote_alert' in config_options:
            self.set_remote_alerting(int(config_options["remote_alert"]))
        if 'remote_alerts' in config_options:
            self.set_remote_alerting(int(config_options["remote_alerts"]))
        if 'recover_command' in config_options:
            self.set_recover_command(config_options["recover_command"])
        if 'gap' in config_options:
            self.set_gap(config_options["gap"])
        self.running_on = self.short_hostname()
        self.name = name

    def set_recover_command(self, command):
        self.recover_command = command

    def short_hostname(self):
        """Get just our machine name.

        TODO: This might actually be redundant. Python probably provides it's own version of this."""

        return (socket.gethostname() + ".").split(".")[0]

    def set_remote_alerting(self, setting):
        """Configure ourselves to be remote alerting (or not)."""
        if setting == 1:
            self.remote_alerting = True
        else:
            self.remote_alerting = False

    def is_remote(self):
        """Check if we're running on this machine, or if we're a remote instance."""
        if self.running_on == self.short_hostname():
            return False
        else:
            return True

    def run_test(self):
        """Override this method to perform the test."""
        raise NotImplementedError

    def virtual_fail_count(self):
        """Return the number of failures we've had past our tolerance."""
        vfs = self.error_count - self.tolerance
        if vfs < 0:
            vfs = 0
        return vfs

    def test_success(self):
        """Returns false if the test has failed."""
        if self.error_count > self.tolerance:
            return False
        else:
            return True

    def first_failure(self):
        """Check if this is our first failure (past tolerance)."""
        if self.error_count == (self.tolerance + 1):
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
        except:
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
        if self.error_count > self.tolerance:
            result = 0
        else:
            result = 1
        try:
            logger.save_result2(name, self)
        except Exception, e:
            sys.stderr.write("%s\n" % e)
            logger.save_result(name, self.type, self.get_params(), result, self.last_result)

    def send_alert(self, name, alerter):
        """Send an alert when we first fail.

        Set first_only to False to generate mail every time.

        To be removed."""

        if self.virtual_fail_count() == 1:
            alerter.send_alert(name, self)

    def get_params(self):
        """Override this method to return a list of parameters (for logging)"""
        raise NotImplementedError

    def set_tolerance(self, tolerance):
        """Set our tolerance."""
        self.tolerance = tolerance

    def set_gap(self, gap):
        """Set our minimum gap."""
        if int(gap) >= 0:
            self.minimum_gap = int(gap)

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

    def record_skip(self, which_dep):
        """Record that we were skipped.

        We pretend to have succeeded as we don't want notifications sent."""
        self.record_success()
        self.was_skipped = True
        self.skip_dep = which_dep

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
        except:
            pass

        if self.last_error_count >= self.tolerance and self.success_count == 1:
            return True
        else:
            return False

    def first_failure_time(self):
        """Get a datetime object showing when we first failed."""
        return self.failed_at

    def get_error_count(self):
        """Get the number of times we've failed (ignoring tolerance)."""
        return self.error_count

    def is_urgent(self):
        """Check if this monitor needs urgent alerts (e.g. SMS)."""
        return self.urgent

    def set_urgency(self, urgency):
        """Record if this monitor needs urgent alerts."""
        if urgency == 1:
            urgency = True
        else:
            urgency = False

        self.urgent = urgency

    def should_run(self):
        """Check if we should run our tests.

        We always run if the minimum gap is 0, or if we're currently failing.
        Otherwise, we run if the last time we ran was more than minimum_gap seconds ago.
        """
        now = int(time.time())
        if self.minimum_gap == 0:
            self.last_run = now
            return True
        if self.error_count > 0:
            self.last_run = now
            return True
        if self.last_run == 0:
            self.last_run = now
            return True
        gap = now - self.last_run
        if gap >= self.minimum_gap:
            self.last_run = now
            return True
        return False

    def last_virtual_fail_count(self):
        if (self.last_error_count - self.tolerance) < 0:
            return 0
        else:
            return self.last_error_count - self.tolerance

    def attempt_recover(self):
        if self.recover_command == "":
            self.recover_info = ""
            return
        if not self.first_failure():
            return

        try:
            p = subprocess.Popen(self.recover_command.split(' '))
            p.wait()
            self.recover_info = "Command executed and returned %d" % p.returncode
        except Exception, e:
            self.recover_info = "Unable to run command: %s" % e

        return

    def post_config_setup(self):
        """ any post config setup needed """
        pass


class MonitorFail(Monitor):
    """A monitor which always fails.

    Use for testing alerters etc."""

    type = "fail"

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        if 'interval' in config_options:
            self.interval = int(config_options["interval"])
        else:
            self.interval = 5

    def run_test(self):
        """Always fails."""
        print "error_count = %d, interval = %d --> %d" % (self.error_count, self.interval, self.error_count % self.interval)
        if (self.interval == 0) or (self.error_count == 0) or (self.error_count % self.interval != 0):
            self.record_fail("This monitor always fails.")
            return False
        else:
            self.record_success()
            return True

    def describe(self):
        return "A monitor which always fails."

    def get_params(self):
        return (self.interval,)


class MonitorNull(Monitor):
    """A monitor which always passes."""

    type = "null"

    def run_test(self):
        self.record_success()

    def get_params(self):
        return ()
