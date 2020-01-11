import os
import re
import shlex
import subprocess
import time
from typing import Optional, Tuple

from .monitor import Monitor, register

try:
    import win32api

    win32_available = True
except ImportError:
    win32_available = False


def _size_string_to_bytes(s: str) -> Optional[int]:
    if s is None:
        return None
    if s.endswith("G"):
        gigs = int(s[:-1])
        bytes = gigs * (1024 ** 3)
    elif s.endswith("M"):
        megs = int(s[:-1])
        bytes = megs * (1024 ** 2)
    elif s.endswith("K"):
        kilos = int(s[:-1])
        bytes = kilos * 1024
    else:
        return int(s)
    return bytes


def _bytes_to_size_string(b: int) -> str:
    """Convert a number in bytes to a sensible unit."""

    kb = 1024
    mb = kb * 1024
    gb = mb * 1024
    tb = gb * 1024

    if b > tb:
        return "%0.2fTiB" % (b / float(tb))
    elif b > gb:
        return "%0.2fGiB" % (b / float(gb))
    elif b > mb:
        return "%0.2fMiB" % (b / float(mb))
    elif b > kb:
        return "%0.2fKiB" % (b / float(kb))
    else:
        return str(b)


@register
class MonitorDiskSpace(Monitor):
    """Make sure we have enough disk space."""

    type = "diskspace"

    def __init__(self, name: str, config_options: dict) -> None:
        Monitor.__init__(self, name, config_options)
        if self.is_windows(allow_cygwin=False):
            self.use_statvfs = False
            if not win32_available:
                raise RuntimeError(
                    "win32api is not available, but is needed for DiskSpace monitor."
                )
        else:
            self.use_statvfs = True
        self.partition = Monitor.get_config_option(
            config_options, "partition", required=True
        )
        self.limit = _size_string_to_bytes(
            Monitor.get_config_option(config_options, "limit", required=True)
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
        except Exception as e:
            return self.record_fail("Couldn't get free disk space: %s" % e)

        if self.limit and space <= self.limit:
            return self.record_fail(
                "%s free (%d%%)" % (_bytes_to_size_string(space), percent)
            )
        return self.record_success(
            "%s free (%d%%)" % (_bytes_to_size_string(space), percent)
        )

    def describe(self) -> str:
        """Explains what we do."""
        if self.limit is None:
            limit = "none"
        else:
            limit = _bytes_to_size_string(self.limit)

        return "Checking for at least %s free space on %s" % (limit, self.partition)

    def get_params(self) -> Tuple:
        return (self.limit, self.partition)


@register
class MonitorFileStat(Monitor):
    """Make sure a file exists, isn't too old and/or isn't too small."""

    type = "filestat"

    def __init__(self, name: str, config_options: dict) -> None:
        Monitor.__init__(self, name, config_options)
        self.maxage = Monitor.get_config_option(
            config_options, "maxage", required_type="int", minimum=0
        )
        self.minsize = Monitor.get_config_option(
            config_options, "minsize", required_type="str", allow_empty=False
        )
        if self.minsize:
            self.minsize = _size_string_to_bytes(self.minsize)
        self.filename = Monitor.get_config_option(
            config_options, "filename", required=True
        )

    def run_test(self) -> bool:
        try:
            statinfo = os.stat(self.filename)
        except Exception as e:
            return self.record_fail("Unable to check file: %s" % e)

        if self.minsize:
            if statinfo.st_size < self.minsize:
                return self.record_fail(
                    "Size is %d, should be >= %d bytes"
                    % (statinfo.st_size, self.minsize)
                )

        if self.maxage:
            now = time.time()
            diff = now - statinfo.st_mtime
            if diff > self.maxage:
                return self.record_fail(
                    "Age is %d, should be < %d seconds" % (diff, self.maxage)
                )

        return self.record_success()

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

    type = "apcupsd"

    def __init__(self, name: str, config_options: dict) -> None:
        Monitor.__init__(self, name, config_options)
        self.path = Monitor.get_config_option(config_options, "path", default="")

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
            _output = subprocess.check_output(executable)
            output = _output.decode("utf-8")  # type: str
        except subprocess.CalledProcessError as e:
            output = e.output
        except OSError as e:
            return self.record_fail("Could not run {0}: {1}".format(executable, e))
        except OSError as e:
            return self.record_fail("Error while getting UPS info: {0}".format(e))

        for line in output.splitlines():
            if line.find(":") > -1:
                bits = line.split(":")
                info[bits[0].strip()] = bits[1].strip()

        if "STATUS" not in info:
            return self.record_fail("Could not get UPS status")

        if not info["STATUS"] == "ONLINE":
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

    type = "portaudit"
    regexp = re.compile(r"(\d+) problem\(s\) in your installed packages found")

    def __init__(self, name: str, config_options: dict) -> None:
        Monitor.__init__(self, name, config_options)
        self.path = Monitor.get_config_option(config_options, "path", default="")

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
                output = subprocess.check_output([self.path, "-a", "-X", "1"]).decode(
                    "utf-8"
                )
            except subprocess.CalledProcessError as e:
                output = e.output
            except OSError as e:
                return self.record_fail("Error running %s: %s" % (self.path, e))
            except Exception as e:
                return self.record_fail("Error running portaudit: %s" % e)

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
        except Exception as e:
            return self.record_fail("Could not run portaudit: %s" % e)


@register
class MonitorPkgAudit(Monitor):
    """Check a host doesn't have outstanding security issues."""

    type = "pkgaudit"
    regexp = re.compile(r"(\d+) problem\(s\) in \w+ installed package(s|\(s\)) found")
    path = ""

    def __init__(self, name: str, config_options: dict) -> None:
        Monitor.__init__(self, name, config_options)
        self.path = Monitor.get_config_option(config_options, "path", default="")

    def describe(self) -> str:
        return "Checking for insecure packages."

    def get_params(self) -> Tuple:
        return (self.path,)

    def run_test(self) -> bool:
        try:
            if self.path == "":
                self.path = "/usr/local/sbin/pkg"
            try:
                output = subprocess.check_output([self.path, "audit"]).decode("utf-8")
            except subprocess.CalledProcessError as e:
                output = e.output.decode("utf-8")
            except OSError as e:
                return self.record_fail(
                    "Failed to run %s audit: {0} {1}".format(self.path, e)
                )
            except Exception as e:
                return self.record_fail("Error running pkg audit: {0}".format(e))

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
        except Exception as e:
            return self.record_fail("Could not run pkg: %s" % e)


@register
class MonitorLoadAvg(Monitor):
    """Check a host's load average isn't too high."""

    type = "loadavg"

    def __init__(self, name: str, config_options: dict) -> None:
        Monitor.__init__(self, name, config_options)
        if self.is_windows(allow_cygwin=False):
            raise RuntimeError("loadavg monitor does not support Windows")
        # which time field we're looking at: 0 = 1min, 1 = 5min, 2=15min
        self.which = Monitor.get_config_option(
            config_options,
            "which",
            required_type="int",
            default=1,
            minimum=0,
            maximum=2,
        )
        self.max = Monitor.get_config_option(
            config_options, "max", required_type="float", default=1.00, minimum=0
        )

    def describe(self) -> str:
        if self.which == 0:
            return "Checking 1min loadavg is <= %0.2f" % self.max
        elif self.which == 1:
            return "Checking 5min loadavg is <= %0.2f" % self.max
        else:
            return "Checking 15min loadavg is <= %0.2f" % self.max

    def run_test(self) -> bool:
        try:
            loadavg = os.getloadavg()
        except Exception as e:
            return self.record_fail("Exception getting loadavg: %s" % e)

        if loadavg[self.which] > self.max:
            return self.record_fail("%0.2f" % loadavg[self.which])
        return self.record_success("%0.2f" % loadavg[self.which])

    def get_params(self) -> Tuple:
        return (self.which, self.max)


@register
class MonitorZap(Monitor):
    """Checks a Zap channel to make sure it is ok"""

    type = "zap"
    r = re.compile("^alarms=(?P<status>).+")

    def __init__(self, name: str, config_options: dict) -> None:
        Monitor.__init__(self, name, config_options)
        self.span = Monitor.get_config_option(
            config_options, "span", required_type="int", default=1, minimum=1
        )

    def run_test(self) -> bool:
        try:
            _output = subprocess.check_output(["ztscan", str(self.span)])
            output = _output.decode("utf-8")
            for line in output:
                matches = self.r.match(line)
                if matches:
                    status = matches.group("status")
                    if status != "OK":
                        return self.record_fail("status is %s" % status)
                    return self.record_success()
            return self.record_fail("Error getting status")
        except Exception as e:
            return self.record_fail("Error running ztscan: %s" % e)

    def describe(self) -> str:
        return "Checking status of zap span %d is OK" % self.span

    def get_params(self) -> Tuple:
        return (self.span,)


@register
class MonitorCommand(Monitor):
    """Check the output of a command.

    We can check for a regexp match in the output or give a max value and check the output is lower that this value.
    """

    result_regexp = None
    type = "command"
    available = True

    def __init__(self, name: str, config_options: dict) -> None:
        Monitor.__init__(self, name, config_options)

        self.result_regexp_text = Monitor.get_config_option(
            config_options, "result_regexp", default=""
        )
        self.result_max = Monitor.get_config_option(
            config_options, "result_max", required_type="int"
        )
        if self.result_regexp_text != "":
            self.result_regexp = re.compile(self.result_regexp_text)
            if self.result_max is not None:
                self.monitor_logger.error(
                    "command monitors do not support result_regexp AND result_max settings simultaneously"
                )
                self.result_max = None

        command = Monitor.get_config_option(
            config_options, "command", required=True, allow_empty=False
        )
        self.command = shlex.split(command)

    def run_test(self) -> bool:
        if not self.available:
            return self.record_skip(None)
        try:
            _out = subprocess.check_output(self.command)
            if self.result_regexp is not None:
                out = _out.decode("utf-8")
                matches = self.result_regexp.search(out)
                if matches:
                    return self.record_success()
                return self.record_fail("could not match regexp in out")
            elif self.result_max is not None:
                outasinteger = int(_out)
                if outasinteger < self.result_max:
                    return self.record_success(
                        "%s < %s" % (outasinteger, self.result_max)
                    )
                return self.record_fail("%s >= %s" % (outasinteger, self.result_max))
            return self.record_success()
        except Exception as e:
            return self.record_fail(str(e))

        return self.record_fail()

    def describe(self) -> str:
        """Explains what this instance is checking"""
        if self.result_regexp is not None:
            return 'checking command "%s" match a regexp %s' % (
                " ".join(self.command),
                self.result_regexp_text,
            )
        elif self.result_max is not None:
            return 'checking command "%s" returns a value < %d' % (
                " ".join(self.command),
                self.result_max,
            )
        else:
            return 'checking command "%s" has return status 0' % " ".join(self.command)

    def get_params(self) -> Tuple:
        return (self.command, self.result_regexp_text, self.result_max)
