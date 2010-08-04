import re
import os

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
            bytes = gigs * (1024**3)
        elif s.endswith("M"):
            megs = int(s[:-1])
            bytes = megs * (1024**2)
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
        if config_options.has_key("path"):
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
        if not info.has_key("STATUS"):
            self.record_fail("Could not get UPS status")
            return False

        if not info["STATUS"] == "ONLINE":
            if info.has_key("TIMELEFT"):
                self.record_fail("%s: %s left" % (info["STATUS"], info["TIMELEFT"]))
                return False
            else:
                self.record_fail(info["STATUS"])
                return False

        data = ""
        if info.has_key("TIMELEFT"):
            data = "%s left" % (info["TIMELEFT"])

        if info.has_key("LOADPCT"):
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
        if config_options.has_key("path"):
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
        if config_options.has_key("which"):
            try:
                which = int(config_options["which"])
            except:
                raise RuntimeError("value of 'which' is not an int")
            if which < 0:
                raise RuntimeError("value of 'which' is too low")
            if which > 2:
                raise RuntimeError("value of 'which' is too high")
            self.which = which
        if config_options.has_key("max"):
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
        if config_options.has_key("span"):
            try:
                self.span = int(config_options["span"])
            except:
                raise RuntimeError("span parameter must be an integer")
            if self.span < 1:
                raise RuntimeError("span parameter must be > 0")

    def run_test(self):
        try:
            pipe = subprocess.Popen(["ztscan", str(self.span)])
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
        except Exception, r:
            self.record_fail("Error running ztscan: %s" % e)
            return False
           
    def describe(self):
        return "Checking status of zap span %d is OK" % self.span

    def get_params(self):
        return (self.span, )

