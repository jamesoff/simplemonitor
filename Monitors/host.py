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
            return "%0.2fTB" % (b / float(tb))
        elif b > gb:
            return "%0.2fGB" % (b / float(gb))
        elif b > mb:
            return "%0.2fMB" % (b / float(mb))
        elif b > kb:
            return "%0.2fKB" % (b / float(kb))
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
            else:
                result = win32api.GetDiskFreeSpaceEx(self.partition)
                space = result[2]
        except Exception, e:
            self.record_fail("Couldn't get free disk space: %s" % e)
            return False

        if space <= self.limit:
            self.record_fail("%s free" % self._bytes_to_size_string(space))
            return False
        else:
            self.record_success("%s free" % self._bytes_to_size_string(space))
            return True

    def describe(self):
        """Explains what we do."""
        return "Checking for at least %s bytes free space on %s" % (self.limit, self.partition)

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


