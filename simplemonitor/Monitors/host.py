"""
Monitor things on a host for SimpleMonitor
"""

import os
import re
import shlex
import subprocess  # nosec
import time
from typing import Tuple, cast

from markupsafe import escape

from ..util import bytes_to_size_string, size_string_to_bytes
from .monitor import Monitor, register

try:
    import psutil
except ImportError:
    psutil = None


try:
    import win32api

    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


@register
class MonitorDiskSpace(Monitor):
    """Make sure we have enough disk space."""

    monitor_type = "diskspace"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        if self.is_windows(allow_cygwin=False):
            self.use_statvfs = False
            if not WIN32_AVAILABLE:
                raise RuntimeError(
                    "win32api is not available, but is needed for DiskSpace monitor."
                )
        else:
            self.use_statvfs = True
        self.partition = self.get_config_option("partition", required=True)
        self.limit = size_string_to_bytes(
            self.get_config_option("limit", required=True)
        )

    def run_test(self) -> bool:
        try:
            if self.use_statvfs:
                result = os.statvfs(self.partition)
                space = result.f_bavail * result.f_frsize
                percent = float(result.f_bavail) / float(result.f_blocks) * 100
            else:
                win_result = win32api.GetDiskFreeSpaceEx(self.partition)
                space = win_result[2]
                percent = float(win_result[2]) / float(win_result[1]) * 100
        except Exception as error:
            return self.record_fail("Couldn't get free disk space: %s" % error)

        if self.limit and space <= self.limit:
            return self.record_fail(
                "%s free (%d%%)" % (bytes_to_size_string(space), percent)
            )
        return self.record_success(
            "%s free (%d%%)" % (bytes_to_size_string(space), percent)
        )

    def describe(self) -> str:
        """Explains what we do."""
        if self.limit is None:
            limit = "none"
        else:
            limit = bytes_to_size_string(self.limit)

        return "Checking for at least %s free space on %s" % (limit, self.partition)

    def get_params(self) -> Tuple:
        return (self.limit, self.partition)


@register
class MonitorFileStat(Monitor):
    """Make sure a file exists, isn't too old and/or isn't too small."""

    monitor_type = "filestat"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self.maxage = self.get_config_option("maxage", required_type="int", minimum=0)
        _minsize = self.get_config_option(
            "minsize", required_type="str", allow_empty=True
        )
        if _minsize:
            self.minsize = size_string_to_bytes(_minsize)
        else:
            self.minsize = None
        _maxsize = self.get_config_option(
            "maxsize", required_type="str", allow_empty=True, default=""
        )
        if _maxsize:
            self.maxsize = size_string_to_bytes(_maxsize)
        else:
            self.maxsize = None
        self.filename = self.get_config_option("filename", required=True)

    def run_test(self) -> bool:
        try:
            statinfo = os.stat(self.filename)
        except FileNotFoundError:
            return self.record_fail("File %s does not exist" % self.filename)
        except Exception as error:
            return self.record_fail("Unable to check file: %s" % error)

        if self.minsize:
            if statinfo.st_size < self.minsize:
                return self.record_fail(
                    "Size is %d, should be >= %d bytes"
                    % (statinfo.st_size, self.minsize)
                )

        if self.maxsize:
            if statinfo.st_size > self.maxsize:
                return self.record_fail(
                    "Size is %d, should be <= %d bytes"
                    % (statinfo.st_size, self.maxsize)
                )

        now = time.time()
        diff = now - statinfo.st_mtime
        if self.maxage:
            if diff > self.maxage:
                return self.record_fail(
                    "Age is %d, should be < %d seconds" % (diff, self.maxage)
                )

        return self.record_success(
            "File {} exists (age: {}, size: {})".format(
                self.filename, int(diff), statinfo.st_size
            )
        )

    def describe(self) -> str:
        """Explains what we do"""
        desc = "Checking %s exists" % self.filename
        if self.maxage:
            desc = desc + " and is not older than %d seconds" % self.maxage
        if self.minsize:
            desc = desc + " and is not smaller than %d bytes" % self.minsize
        return desc

    def get_params(self) -> Tuple:
        return (self.filename, self.minsize, self.maxage)


@register
class MonitorApcupsd(Monitor):
    """Monitor an APC UPS (with apcupsd) to make sure it's ONLINE.

    Note: You must have apcupsd successfully setup and working for this monitor
    to function.
    """

    monitor_type = "apcupsd"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self.path = self.get_config_option("path", default="")

    def run_test(self) -> bool:
        info = {}
        if self.path != "":
            executable = os.path.join(self.path, "apcaccess")
        else:
            if self.is_windows():
                executable = os.path.join("c:\\", "apcupsd", "bin", "apcaccess.exe")
            else:
                executable = "apcaccess"
        try:
            _output = subprocess.check_output(executable)  # nosec
            output = _output.decode("utf-8")  # type: str
        except subprocess.CalledProcessError as error:
            output = error.output
        except OSError as error:
            return self.record_fail("Could not run {0}: {1}".format(executable, error))
        except Exception as error:
            return self.record_fail("Error while getting UPS info: {0}".format(error))

        for line in output.splitlines():
            if line.find(":") > -1:
                bits = line.split(":")
                info[bits[0].strip()] = bits[1].strip()

        if "STATUS" not in info:
            return self.record_fail("Could not get UPS status")

        if info["STATUS"] != "ONLINE":
            if "TIMELEFT" in info:
                return self.record_fail(
                    "%s: %s left" % (info["STATUS"], info["TIMELEFT"])
                )
            return self.record_fail(info["STATUS"])

        data = ""
        if "TIMELEFT" in info:
            data = "%s left" % (info["TIMELEFT"])

        if "LOADPCT" in info:
            if data != "":
                data += "; "
            data += "%s%% load" % info["LOADPCT"][0:4]

        return self.record_success(data)

    def describe(self) -> str:
        return "Monitoring UPS to make sure it's ONLINE."

    def get_params(self) -> Tuple:
        return (self.path,)


@register
class MonitorPortAudit(Monitor):
    """Check a host doesn't have outstanding security issues."""

    monitor_type = "portaudit"
    regexp = re.compile(r"(\d+) problem\(s\) in your installed packages found")

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self.path = self.get_config_option("path", default="")

    def describe(self) -> str:
        return "Checking for insecure ports."

    def get_params(self) -> Tuple:
        return (self.path,)

    def run_test(self) -> bool:
        try:
            # -X 1 tells portaudit to re-download db if one day out of date
            if self.path == "":
                self.path = "/usr/local/sbin/portaudit"
            try:
                # nosec
                _output = subprocess.check_output([self.path, "-a", "-X", "1"])  # nosec
                output = _output.decode("utf-8")
            except subprocess.CalledProcessError as error:
                output = error.output
            except OSError as error:
                return self.record_fail("Error running %s: %s" % (self.path, error))
            except Exception as error:
                return self.record_fail("Error running portaudit: %s" % error)

            for line in output.splitlines():
                matches = self.regexp.match(line)
                if matches:
                    count = int(matches.group(1))
                    # sanity check
                    if count == 0:
                        return self.record_success()
                    if count == 1:
                        return self.record_fail("1 problem")
                    return self.record_fail("%d problems" % count)
            return self.record_success()
        except Exception as error:
            return self.record_fail("Could not run portaudit: %s" % error)


@register
class MonitorPkgAudit(Monitor):
    """Check a host doesn't have outstanding security issues."""

    monitor_type = "pkgaudit"
    regexp = re.compile(r"(\d+) problem\(s\) in \w+ installed package(s|\(s\)) found")
    path = ""

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self.path = self.get_config_option("path", default="")

    def describe(self) -> str:
        return "Checking for insecure packages."

    def get_params(self) -> Tuple:
        return (self.path,)

    def run_test(self) -> bool:
        try:
            if self.path == "":
                self.path = "/usr/local/sbin/pkg"
            try:
                _output = subprocess.check_output([self.path, "audit"])  # nosec
                output = _output.decode("utf-8")
            except subprocess.CalledProcessError as error:
                output = error.output.decode("utf-8")
            except OSError as error:
                return self.record_fail(
                    "Failed to run %s audit: {0} {1}".format(self.path, error)
                )
            except Exception as error:
                return self.record_fail("Error running pkg audit: {0}".format(error))

            for line in output.splitlines():
                matches = self.regexp.match(line)
                if matches:
                    count = int(matches.group(1))
                    # sanity check
                    if count == 0:
                        return self.record_success()
                    if count == 1:
                        return self.record_fail("1 problem")
                    return self.record_fail("%d problems" % count)
            return self.record_success()
        except Exception as error:
            return self.record_fail("Could not run pkg: %s" % error)


@register
class MonitorLoadAvg(Monitor):
    """Check a host's load average isn't too high."""

    monitor_type = "loadavg"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        if self.is_windows(allow_cygwin=False):
            raise RuntimeError("loadavg monitor does not support Windows")
        # which time field we're looking at: 0 = 1min, 1 = 5min, 2=15min
        self.which = self.get_config_option(
            "which", required_type="int", default=1, minimum=0, maximum=2
        )
        self.max = self.get_config_option(
            "max", required_type="float", default=1.00, minimum=0
        )

    def describe(self) -> str:
        if self.which == 0:
            return "Checking 1min loadavg is <= %0.2f" % self.max
        if self.which == 1:
            return "Checking 5min loadavg is <= %0.2f" % self.max
        return "Checking 15min loadavg is <= %0.2f" % self.max

    def run_test(self) -> bool:
        try:
            loadavg = os.getloadavg()
        except Exception as error:
            return self.record_fail("Exception getting loadavg: %s" % error)

        if loadavg[self.which] > self.max:
            return self.record_fail("%0.2f" % loadavg[self.which])
        return self.record_success("%0.2f" % loadavg[self.which])

    def get_params(self) -> Tuple:
        return (self.which, self.max)


@register
class MonitorMemory(Monitor):
    """Check for available memory."""

    monitor_type = "memory"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        if psutil is None:
            self.monitor_logger.critical("psutil is not installed.")
            self.monitor_logger.critical("Try: pip install -r requirements.txt")
        self.percent_free = cast(
            int,
            self.get_config_option("percent_free", required_type="int", required=True),
        )

    def run_test(self) -> bool:
        if psutil is None:
            return self.record_fail("psutil is not installed")
        stats = psutil.virtual_memory()
        percent = int(stats.available / stats.total * 100)
        message = "{}% free".format(percent)
        if percent < self.percent_free:
            return self.record_fail(message)
        return self.record_success(message)

    def get_params(self) -> Tuple:
        return (self.percent_free,)

    def describe(self) -> str:
        return "Checking for at least {}% free memory".format(self.percent_free)


@register
class MonitorSwap(Monitor):
    """Check for available swap."""

    monitor_type = "swap"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        if psutil is None:
            self.monitor_logger.critical("psutil is not installed.")
            self.monitor_logger.critical("Try: pip install -r requirements.txt")
        self.percent_free = cast(
            int,
            self.get_config_option("percent_free", required_type="int", required=True),
        )

    def run_test(self) -> bool:
        if psutil is None:
            return self.record_fail("psutil is not installed")
        stats = psutil.swap_memory()
        percent = 100 - stats.percent
        message = f"{percent:.2f}% free"
        if percent < self.percent_free:
            return self.record_fail(message)
        return self.record_success(message)

    def get_params(self) -> Tuple:
        return (self.percent_free,)

    def describe(self) -> str:
        return f"Checking for at least {self.percent_free}% free swap"


@register
class MonitorZap(Monitor):
    """Checks a Zap channel to make sure it is ok"""

    monitor_type = "zap"
    r = re.compile("^alarms=(?P<status>).+")

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self.span = self.get_config_option(
            "span", required_type="int", default=1, minimum=1
        )

    def run_test(self) -> bool:
        try:
            _output = subprocess.check_output(["ztscan", str(self.span)])  # nosec
            output = _output.decode("utf-8")
            for line in output:
                matches = self.r.match(line)
                if matches:
                    status = matches.group("status")
                    if status != "OK":
                        return self.record_fail("status is %s" % status)
                    return self.record_success()
            return self.record_fail("Error getting status")
        except Exception as error:
            return self.record_fail("Error running ztscan: %s" % error)

    def describe(self) -> str:
        return "Checking status of zap span %d is OK" % self.span

    def get_params(self) -> Tuple:
        return (self.span,)


@register
class MonitorCommand(Monitor):
    """Check the output of a command.

    We can check for a regexp match in the output or give a max value and check the
    output is lower than this value.
    """

    result_regexp = None
    monitor_type = "command"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)

        self.result_regexp_text = self.get_config_option("result_regexp", default="")
        self.result_max = self.get_config_option("result_max", required_type="int")
        if self.result_regexp_text != "":
            self.result_regexp = re.compile(self.result_regexp_text)
            if self.result_max is not None:
                self.monitor_logger.error(
                    "command monitors do not support result_regexp AND"
                    "result_max settings simultaneously"
                )
                self.result_max = None
        self.show_output = self.get_config_option(
            "show_output", required_type="bool", default=False
        )

        command = self.get_config_option("command", required=True, allow_empty=False)
        self.command = shlex.split(command)

    def run_test(self) -> bool:
        try:
            _out = subprocess.check_output(self.command)  # nosec
            if self.result_regexp is not None:
                out = _out.decode("utf-8")
                matches = self.result_regexp.search(out)
                if matches:
                    return self.record_success()
                return self.record_fail("could not match regexp in out")
            if self.result_max is not None:
                outasinteger = int(_out)
                if outasinteger < self.result_max:
                    return self.record_success(
                        "%s < %s" % (outasinteger, self.result_max)
                    )
                return self.record_fail("%s >= %s" % (outasinteger, self.result_max))
            msg = ""
            if self.show_output:
                msg = escape(_out.decode("utf-8"))
            return self.record_success(msg)
        except subprocess.CalledProcessError as exception:
            if self.show_output:
                return self.record_fail(exception.output.decode("utf-8"))
            return self.record_fail(str(exception))
        except Exception as exception:
            return self.record_fail(str(exception))

    def describe(self) -> str:
        """Explains what this instance is checking"""
        if self.result_regexp is not None:
            return 'checking command "%s" match a regexp %s' % (
                " ".join(self.command),
                self.result_regexp_text,
            )
        if self.result_max is not None:
            return 'checking command "%s" returns a value < %d' % (
                " ".join(self.command),
                self.result_max,
            )
        return "checking command '%s' has return status 0" % " ".join(self.command)

    def get_params(self) -> Tuple:
        return (
            self.command,
            self.result_regexp_text,
            self.result_max,
            self.show_output,
        )
