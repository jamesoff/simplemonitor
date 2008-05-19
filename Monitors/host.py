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
            self.record_fail("%d bytes available" % space)
            return False
        else:
            self.record_success()
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
                matches = self.regexp.match(line)
                if matches:
                    status = matches.group(1)
                    status = status.strip()
                    if status.startswith("ONLINE"):
                        self.record_success()
                        return True
                    else:
                        self.record_fail("UPS status is %s" % status)
                        return False
        except Exception, e:
            self.record_fail("Could not run %s: %s" % (executable, e))
            return False

    def describe(self):
        return "Monitoring UPS to make sure it's ONLINE."

    def get_params(self):
        return (self.path, )


