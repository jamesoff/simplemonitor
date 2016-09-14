import re
import os
import subprocess
import time

try:
    import win32api
    win32_available = True
except:
    win32_available = False

from monitor import Monitor


class MonitorDiskSpace(Monitor):
    """Make sure we have enough disk space."""

    type = "diskspace"

    def _size_string_to_bytes(self, s):
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

    def _bytes_to_size_string(self, b):
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

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        if self.is_windows(allow_cygwin=False):
            self.use_statvfs = False
            if not win32_available:
                raise RuntimeError("win32api is not available, but is needed for DiskSpace monitor.")
        else:
            self.use_statvfs = True
        try:
            partition = config_options["partition"]
            limit = config_options["limit"]
        except:
            raise RuntimeError("Required configuration fields missing")
        self.partition = partition
        self.limit = self._size_string_to_bytes(limit)

    def run_test(self):
        try:
            if self.use_statvfs:
                result = os.statvfs(self.partition)
                space = result.f_bavail * result.f_frsize
                percent = float(result.f_bavail) / float(result.f_blocks) * 100
            else:
                result = win32api.GetDiskFreeSpaceEx(self.partition)
                space = result[2]
                percent = float(result[2]) / float(result[1]) * 100
        except Exception, e:
            self.record_fail("Couldn't get free disk space: %s" % e)
            return False

        if space <= self.limit:
            self.record_fail("%s free (%d%%)" % (self._bytes_to_size_string(space), percent))
            return False
        else:
            self.record_success("%s free (%d%%)" % (self._bytes_to_size_string(space), percent))
            return True

    def describe(self):
        """Explains what we do."""
        return "Checking for at least %s free space on %s" % (self._bytes_to_size_string(self.limit), self.partition)

    def get_params(self):
        return (self.limit, self.partition)


class MonitorFileStat(Monitor):
    """Make sure a file exists, isn't too old and/or isn't too small."""

    type = "filestat"
    maxage = -1
    minsize = -1
    filename = ""

    def _size_string_to_bytes(self, s):
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

    def _bytes_to_size_string(self, b):
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

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        try:
            if 'maxage' in config_options:
                maxage = int(config_options["maxage"])
                self.maxage = maxage
        except:
            raise RuntimeError("Maxage missing or not an integer (number of seconds)")

        try:
            if 'minsize' in config_options:
                minsize = self._size_string_to_bytes(config_options["minsize"])
                self.minsize = minsize
        except:
            raise RuntimeError("Minsize missing or not an integer (number of bytes")

        try:
            filename = config_options["filename"]
        except:
            raise RuntimeError("Filename missing")

        self.filename = filename

    def run_test(self):
        try:
            statinfo = os.stat(self.filename)
        except Exception, e:
            self.record_fail("Unable to check file: %s" % e)
            return False

        if (self.minsize >= 0):
            if (statinfo.st_size < self.minsize):
                    self.record_fail("Size is %d, should be >= %d bytes" % (statinfo.st_size, self.minsize))
                    return False

        if (self.maxage >= 0):
            now = time.time()
            diff = now - statinfo.st_mtime
            if (diff > self.maxage):
                self.record_fail("Age is %d, should be < %d seconds" % (diff, self.maxage))
                return False

        self.record_success()
        return True

    def describe(self):
        """Explains what we do"""
        desc = "Checking %s exists" % self.filename
        if (self.maxage >= 0):
            desc = desc + " and is not older than %d seconds" % self.maxage
        if (self.minsize >= 0):
            desc = desc + " and is not smaller than %d bytes" % self.minsize
        return desc

    def get_params(self):
        return (self.filename, self.minsize, self.maxage)


class MonitorApcupsd(Monitor):
    """Monitor an APC UPS (with apcupsd) to make sure it's ONLINE.

    Note: You must have apcupsd successfully setup and working for this monitor
    to function.
    """

    type = "apcupsd"

    path = ""
    regexp = re.compile("STATUS +: (.+)")

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        if 'path' in config_options:
            self.path = config_options["path"]

    def run_test(self):
        info = {}
        if self.path != "":
            executable = os.path.join(self.path, "apcaccess")
        else:
            if self.is_windows():
                executable = os.path.join("c:\\", "apcupsd", "bin", "apcaccess.exe")
            else:
                executable = "apcaccess"
        try:
            process_handle = os.popen(executable)
            for line in process_handle:
                if line.find(":") > -1:
                    bits = line.split(":")
                    info[bits[0].strip()] = bits[1].strip()

        except Exception, e:
            self.record_fail("Could not run %s: %s" % (executable, e))
            return False
        if 'STATUS' not in info:
            self.record_fail("Could not get UPS status")
            return False

        if not info["STATUS"] == "ONLINE":
            if 'TIMELEFT' in info:
                self.record_fail("%s: %s left" % (info["STATUS"], info["TIMELEFT"]))
                return False
            else:
                self.record_fail(info["STATUS"])
                return False

        data = ""
        if 'TIMELEFT' in info:
            data = "%s left" % (info["TIMELEFT"])

        if 'LOADPCT' in info:
            if data != "":
                data += "; "
            data += "%s%% load" % info["LOADPCT"][0:4]

        self.record_success(data)
        return True

    def describe(self):
        return "Monitoring UPS to make sure it's ONLINE."

    def get_params(self):
        return (self.path, )


class MonitorPortAudit(Monitor):
    """Check a host doesn't have outstanding security issues."""

    type = "portaudit"
    regexp = re.compile("(\d+) problem\(s\) in your installed packages found")
    path = ""

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        if 'path' in config_options:
            self.path = config_options["path"]

    def describe(self):
        return "Checking for insecure ports."

    def get_params(self):
        return (self.path, )

    def run_test(self):
        try:
            # -X 1 tells portaudit to re-download db if one day out of date
            if self.path == "":
                self.path = "/usr/local/sbin/portaudit"
            process_handle = os.popen("%s -a -X 1" % self.path)
            for line in process_handle:
                matches = self.regexp.match(line)
                if matches:
                    count = int(matches.group(1))
                    # sanity check
                    if count == 0:
                        self.record_success()
                        return True
                    if count == 1:
                        self.record_fail("1 problem")
                    else:
                        self.record_fail("%d problems" % count)
                    return False
            self.record_success()
            return True
        except Exception, e:
            self.record_fail("Could not run portaudit: %s" % e)
            return False


class MonitorPkgAudit(Monitor):
    """Check a host doesn't have outstanding security issues."""

    type = "pkgaudit"
    regexp = re.compile("(\d+) problem\(s\) in the installed packages found")
    path = ""

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        if 'path' in config_options:
            self.path = config_options["path"]

    def describe(self):
        return "Checking for insecure packages."

    def get_params(self):
        return (self.path, )

    def run_test(self):
        try:
            if self.path == "":
                self.path = "/usr/local/sbin/pkg"
            process_handle = os.popen("%s audit" % self.path)
            for line in process_handle:
                matches = self.regexp.match(line)
                if matches:
                    count = int(matches.group(1))
                    # sanity check
                    if count == 0:
                        self.record_success()
                        return True
                    if count == 1:
                        self.record_fail("1 problem")
                    else:
                        self.record_fail("%d problems" % count)
                    return False
            self.record_success()
            return True
        except Exception, e:
            self.record_fail("Could not run pkg: %s" % e)
            return False


class MonitorLoadAvg(Monitor):
    """Check a host's load average isn't too high."""

    type = "loadavg"
    # which time field we're looking at: 0 = 1min, 1 = 5min, 2=15min
    which = 1
    max = 1.00

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        if self.is_windows(allow_cygwin=False):
            raise RuntimeError("loadavg monitor does not support Windows")
        if 'which' in config_options:
            try:
                which = int(config_options["which"])
            except:
                raise RuntimeError("value of 'which' is not an int")
            if which < 0:
                raise RuntimeError("value of 'which' is too low")
            if which > 2:
                raise RuntimeError("value of 'which' is too high")
            self.which = which
        if 'max' in config_options:
            try:
                max = float(config_options["max"])
            except:
                raise RuntimeError("value of 'max' is not a float")
            if max <= 0:
                raise RuntimeError("value of 'max' is too low")
            self.max = max

    def describe(self):
        if self.which == 0:
            return "Checking 1min loadavg is <= %0.2f" % self.max
        elif self.which == 1:
            return "Checking 5min loadavg is <= %0.2f" % self.max
        else:
            return "Checking 15min loadavg is <= %0.2f" % self.max

    def run_test(self):
        try:
            loadavg = os.getloadavg()
        except Exception, e:
            self.record_fail("Exception getting loadavg: %s" % e)
            return False

        if loadavg[self.which] > self.max:
            self.record_fail("%0.2f" % loadavg[self.which])
            return False
        else:
            self.record_success("%0.2f" % loadavg[self.which])
            return True

    def get_params(self):
        return (self.which, self.max)


class MonitorZap(Monitor):
    """Checks a Zap channel to make sure it is ok"""

    type = "zap"
    span = 1
    r = re.compile("^alarms=(?P<status>).+")

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        if 'span' in config_options:
            try:
                self.span = int(config_options["span"])
            except:
                raise RuntimeError("span parameter must be an integer")
            if self.span < 1:
                raise RuntimeError("span parameter must be > 0")

    def run_test(self):
        try:
            pipe = subprocess.Popen(["ztscan", str(self.span)], stdout=subprocess.PIPE).stdout
            for line in pipe:
                matches = self.r.match(line)
                if matches:
                    status = matches.group("status")
                    if status != "OK":
                        self.record_fail("status is %s" % status)
                        return False
                    else:
                        self.record_success()
                        return True
            self.record_fail("Error getting status")
            return False
        except Exception, e:
            self.record_fail("Error running ztscan: %s" % e)
            return False

    def describe(self):
        return "Checking status of zap span %d is OK" % self.span

    def get_params(self):
        return (self.span, )


class MonitorCommand(Monitor):
    """Check the output of a command.

    We can check for a regexp match in the ouput or give a max value and check the output is lower that this value.
    """

    command = ""
    result_regexp = None
    result_regexp_text = ""
    result_max = None

    type = "command"

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)

        self.result_regexp_text = ""
        self.result_regexp = None
        self.result_max = None

        if 'result_regexp' in config_options:
            self.result_regexp_text = config_options["result_regexp"]
            self.result_regexp = re.compile(self.result_regexp_text)
        elif 'result_max' in config_options:
            self.result_max = int(config_options["result_max"])
        # else:
        #    raise RuntimeError("Required configuration fields missing")

        try:
            command = config_options["command"].split(" ")
        except:
            raise RuntimeError("Required configuration fields missing")
        if command == "":
            raise RuntimeError("missing command")
        self.command = command

    def run_test(self):
        try:
            out = subprocess.check_output(self.command)
            if self.result_regexp is not None:
                matches = self.result_regexp.search(out)
                if matches:
                    self.record_success()
                    return True
                else:
                    self.record_fail('could not match regexp in out')
                    return False
            elif self.result_max is not None:
                outasinteger = int(out)
                if outasinteger < self.result_max:
                    self.record_success("%s < %s" % (outasinteger, self.result_max))
                    return True
                else:
                    self.record_fail("%s >= %s" % (outasinteger, self.result_max))
                    return False
            self.record_success()
            return True
        except Exception, e:
            self.record_fail(e)
            return False

        self.record_fail()
        return False

    def describe(self):
        """Explains what this instance is checking"""
        if self.result_regexp is not None:
            return "checking command \"%s\" match a regexp %s" % (" ".join(self.command), self.result_regexp_text)
        elif self.result_max is not None:
            return "checking command \"%s\" returns a value < %d" % (" ".join(self.command), self.result_max)
        else:
            return "checking command \"%s\" failed" % " ".join(self.command)

    def get_params(self):
        # return (self.command, self.result_regexp_text)
        return (self.command, )
