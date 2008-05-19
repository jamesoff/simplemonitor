
"""A collection of monitors for the SimpleMonitor application.

The Monitor class contains the monitor-independent logic for handling results etc.

Subclasses should provide an __init__(), and override at least run_test() to actually
perform the test. A successful test should call self.record_success() and a failed one
should call self.record_fail(). You should also override the describe() and get_params()
functions.

"""

import socket
import re
import os
import platform
import sys
import datetime
import urllib2
import time

try:
    import win32api
    win32_available = True
except:
    win32_available = False

class Monitor:
    """Simple monitor. This class is abstract."""

    last_result = ""
    is_error = False
    was_error = False
    type = "unknown"
    error_count = 0
    tolerance = 0
    failed_at = None
    # start the success count at 1 so that we don't alert for success as soon as it works
    success_count = 0
    tests_run = 0
    last_error_count = 0

    minimum_gap = 0
    last_run = 0
    
    # dependencies holds master list
    dependencies = []

    # deps holds temporary list
    deps = []

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
        self.deps = self.dependencies

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
        self.dependencies = dependencies
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
        if gap >= 0:
            self.minimum_gap = gap

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

    def record_fail(self, message = ""):
        """Update internal state to show that we had a failure."""
        self.error_count += 1
        self.was_error = self.is_error
        self.is_error = True
        self.last_result = message
        self.failed_at = datetime.datetime.now()
        self.success_count = 0
        self.tests_run += 1
        self.was_skipped = False

    def record_success(self):
        """Update internal state to show we had a success."""
        if self.error_count > 0:
            self.last_error_count = self.error_count
        self.error_count = 0
        self.was_error = self.is_error
        self.is_error = False
        self.last_result = ""
        self.success_count += 1
        self.tests_run += 1
        self.was_skipped = False

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
        if self.was_error and not self.is_error and self.last_error_count >= self.tolerance:
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
        if self.minimum_gap == 0:
            return True
        if self.error_count > 0:
            return True
        now = int(time.time())
        gap = now - self.last_run
        if gap > self.minimum_gap:
            self.last_run = now
            return True
        return False


class MonitorFail(Monitor):
    """A monitor which always fails.

    Use for testing alerters etc."""

    type = "fail"

    def run_test(self):
        """Always fails."""
        if self.virtual_fail_count() < 5:
            self.record_fail("This monitor always fails.")
            return False
        else:
            self.record_success()
            return True

    def describe(self):
        return "A monitor which always fails."

    def get_params(self):
        return ()


class MonitorTCP(Monitor):
    """TCP port monitor"""

    host = ""
    port = ""
    type = "tcp"

    def __init__(self, host, port):
        """Constructor"""
        if host == "":
            raise RuntimeError("missing hostname")
        if port == "" or port <= 0:
            raise RuntimeError("missing or invalid port number")
        self.host = host
        self.port = port

    def run_test(self):
        """Check the port is open on the remote host"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(5.0)
            s.connect((self.host, self.port))
        except:
            self.record_fail()
            return False
        s.close()
        self.record_success()
        return True

    def describe(self):
        """Explains what this instance is checking"""
        return "checking for open tcp socket on %s:%d" % (self.host, self.port)

    def get_params(self):
        return (self.host, self.port)


class MonitorService(Monitor):
    """Monitor a Windows service"""

    service_name = ""
    want_state= "RUNNING"
    host = "."
    type = "service"

    def __init__(self, service_name, want_state, host = "."):
        if service_name == "":
            raise RuntimeError("missing service name")
        if want_state not in ["RUNNING", "STOPPED"]:
            raise RuntimeError("invalid state")

        self.service_name = service_name
        self.want_state = want_state
        self.host = host

    def run_test(self):
        """Check the service is in the desired state"""
        r = re.compile("STATE +: [0-9]+ +%s" % self.want_state)
        try:
            if platform.system() == "CYGWIN_NT-6.0":
                commandline = 'sc \\\\\\\\%s query %s'
            elif platform.system() in ["Microsoft", "Windows"]:
                commandline = 'sc \\\\%s query %s'
            else:
                # we need windows for sc
                self.record_fail("Cannot check for Windows services while running on a non-Windows platform.")
                return False
                
            commandline = commandline % (self.host, self.service_name)
            process_handle = os.popen(commandline)
            for line in process_handle:
                matches = r.search(line)
                if matches:
                    self.record_success()
                    return True
        except Exception, e:
            sys.stderr.write("%s\n" % e)
            pass
        self.record_fail()
        return False

    def describe(self):
        """Explains what this instance is checking"""
        return "checking for service called %s in state %s" % (self.service_name, self.want_state)

    def get_params(self):
        return (self.host, self.service_name, self.want_state)


class MonitorRC(Monitor):
    """Monitor a service handled by an rc.d script.
    
    This monitor checks the return code of /usr/local/etc/rc.d/<name>
    and reports failure if it's non-zero by default.
    """

    type = "rc"

    def __init__(self, service_name, script_path="/usr/local/etc/rc.d/", want_return_code=0):
        """Initialise the class.
        Change script path to /etc/rc.d/ to monitor base system services. If the
        script path ends with /, the service name is appended."""
        if service_name == "":
            raise RuntimeError("missing service name")
        if script_path == "":
            raise RuntimeError("missing script path")
        if script_path.endswith("/"):
            script_path = script_path + service_name
        self.script_path = script_path
        self.service_name = service_name
        self.want_return_code = want_return_code
        # Check if we need a .sh (old-style RC scripts in FreeBSD)
        if not os.path.isfile(self.script_path):
            if os.path.isfile(self.script_path + ".sh"):
                self.script_path = self.script_path + ".sh"
            else:
                raise RuntimeError("Script %s(.sh) does not exist" % self.script_path)

    def run_test(self):
        """Check the service is in the desired state."""
        if platform.system() in ["Microsoft", "CYGWIN_NT-6.0"]:
            self.last_result = "Cannot run this monitor on a non-UNIX host."
            self.is_error = True
            return False
        try:
            fh = os.popen("%s status" % self.script_path, "r")
            result = fh.close()
            if result == None:
                result = 0
            if result != self.want_return_code:
                self.record_fail()
                return False
            else:
                self.record_success()
                return True
        except Exception, e:
            self.record_fail("Exception while executing script: %s" % e)
            return False

    def get_params(self):
        return (self.service_name, self.want_return_code)

    def describe(self):
        """Explains what this instance is checking."""
        return "Checks service %s is running" % self.script_path


class MonitorHost(Monitor):
    """Ping a host to make sure it's up"""

    host = ""
    ping_command = ""
    ping_regexp = ""
    type = "host"

    def __init__(self, host):
        if self.is_windows(allow_cygwin=True):
            self.ping_command = "ping -n 1 %s"
            self.ping_regexp = "Reply from "
        else:
            self.ping_command = "ping -c1 %s 2> /dev/null"
            self.ping_regexp = "bytes from"
        if host == "":
            raise RuntimeError("missing hostname")
        self.host = host

    def run_test(self):
        r = re.compile(self.ping_regexp)
        try:
            process_handle = os.popen(self.ping_command % self.host)
            for line in process_handle:
                matches = r.search(line)
                if matches:
                    self.record_success()
                    return True
        except Exception, e:
            raise e
            pass
        self.record_fail()
        return False

    def describe(self):
        """Explains what this instance is checking"""
        return "checking host %s is pingable" % self.host

    def get_params(self):
        return (self.host, )


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

    def __init__(self, partition, limit):
        if self.is_windows(allow_cygwin=False):
            self.use_statvfs = False
            if not win32_available:
                raise RuntimeError("win32api is not available, but is needed for DiskSpace monitor.")
        else:
            self.use_statvfs = True
        self.partition = partition
        self.limit = self._size_string_to_bytes(limit)

    def run_test(self):
        try:
            if self.use_statvfs:
                result = os.statvfs(self.partition)
                space = result.f_bfree * result.f_bsize
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


class MonitorHTTP(Monitor):
    """Check an HTTP server is working right.
    
    We can either check that we get a 200 OK back, or we can check for a regexp match in the page.
    """

    url = ""
    regexp = None
    regexp_text = ""
    allowed_codes = []

    type = "http"

    def __init__(self, url, regexp="", allowed_codes = []):
        self.url = url
        if regexp != "":
            self.regexp = re.compile(regexp)
            self.regexp_text = regexp
        self.allowed_codes = allowed_codes

    def run_test(self):
        try:
            url_handle = urllib2.urlopen(self.url)
            status = "200 OK"
            if hasattr(url_handle, "status"):
                if url_handle.status != "":
                    status = url_handle.status
            if status != "200 OK":
                self.record_fail("Got status '%s' instead of 200 OK" % status)
                return False
            if self.regexp == None:
                self.record_success()
                return True
            else:
                for line in url_handle:
                    matches = self.regexp.search(line)
                    if matches:
                        self.record_success()
                        return True
                self.record_fail("Got 200 OK but couldn't match /%s/ in page." % self.regexp_text)
                return False
        except urllib2.HTTPError, e:
            if e.code in self.allowed_codes:
                self.record_success()
                return True
            self.record_fail("HTTP error while opening URL: %s" % e)
            return False
        except Exception, e:
            self.record_fail("Exception while trying to open url: %s" % e)
            return False

    def describe(self):
        """Explains what we do."""
        if self.regexp == None:
            message = "Checking that accessing %s returns HTTP/200 OK" % self.url
        else:
            message = "Checking that accessing %s returns HTTP/200 OK and that /%s/ matches the page" % (self.url, self.regexp_text)
        return message

    def get_params(self):
        return (self.url, self.regexp_text, self.allowed_codes)


class MonitorApcupsd(Monitor):
    """Monitor an APC UPS (with apcupsd) to make sure it's ONLINE.
    
    Note: You must have apcupsd successfully setup and working for this monitor
    to function.
    """

    type = "apcupsd"

    path = ""
    regexp = re.compile("STATUS +: (.+)")

    def __init__(self, path = ""):
        self.path = path

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
                    if status == "ONLINE":
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


class MonitorSvc(Monitor):
    """Monitor a service handled by daemontools."""

    type = "svc"
    path = ""

    def __init__(self, path):
        self.path = path

    def run_test(self):
        if self.path == "":
            return
        try:
            fh = os.popen("svok %s" % self.path, "r")
            result = fh.close()
            if result == None:
                result = 0
            if result > 0:
                self.record_fail("svok returned %d" % int(result))
                return False
            else:
                self.record_success()
                return True
        except Exception, e:
            self.record_fail("Exception while executing svok: %s" % e)
            return False

    def describe(self):
        return "Checking that the supervise-managed service in %s is running." % self.path

    def get_params(self):
        return (self.path, )
