import platform
import re
import os
import subprocess
import sys

from monitor import Monitor


class MonitorSvc(Monitor):
    """Monitor a service handled by daemontools."""

    type = "svc"
    path = ""

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        try:
            self.path = config_options["path"]
        except:
            raise RuntimeError("Required configuration fields missing")
        self.params = ("svok %s" % self.path).split(" ")

    def run_test(self):
        if self.path == "":
            return
        try:
            result = subprocess.call(self.params)
            if result is None:
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


class MonitorService(Monitor):
    """Monitor a Windows service"""

    service_name = ""
    want_state = "RUNNING"
    host = "."
    type = "service"

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        try:
            service_name = config_options["service"]
        except:
            raise RuntimeError("Required configuration fields missing")
        if 'state' in config_options:
            want_state = config_options["state"]
        else:
            want_state = "RUNNING"

        if 'host' in config_options:
            host = config_options["host"]
        else:
            host = "."

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
                host = '\\\\\\\\' + self.host
            elif platform.system() in ["Microsoft", "Windows"]:
                host = '\\\\' + self.host
            else:
                # we need windows for sc
                self.record_fail("Cannot check for Windows services while running on a non-Windows platform.")
                return False

            output = str(subprocess.check_output(['sc', host, 'query', self.service_name]))
            matches = r.search(output)
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

    def __init__(self, name, config_options):
        """Initialise the class.
        Change script path to /etc/rc.d/ to monitor base system services. If the
        script path ends with /, the service name is appended."""
        Monitor.__init__(self, name, config_options)
        try:
            service_name = config_options["service"]
        except:
            raise RuntimeError("Required configuration fields missing")
        if 'path' in config_options:
            script_path = config_options["path"]
        else:
            script_path = "/usr/local/etc/rc.d/"
        if 'return_code' in config_options:
            want_return_code = int(config_options["return_code"])
        else:
            want_return_code = 0

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
            returncode = subprocess.check_call([self.script_path, 'status'])
            if returncode == self.want_return_code:
                self.record_success()
                return True
        except subprocess.CalledProcessError, e:
            if e.returncode == self.want_return_code:
                self.record_success()
                return True
            returncode = -1
        except Exception, e:
            self.record_fail("Exception while executing script: %s" % e)
            return False
        self.record_fail("Return code: %d (wanted %d)" % (returncode, self.want_return_code))
        return False

    def get_params(self):
        return (self.service_name, self.want_return_code)

    def describe(self):
        """Explains what this instance is checking."""
        return "Checks service %s is running" % self.script_path


class MonitorEximQueue(Monitor):
    """Make sure an exim queue isn't too big."""

    type = "eximqueue"
    max_length = 10
    r = re.compile("(?P<count>\d+) matches out of (?P<total>\d+) messages")
    path = "/usr/local/sbin"

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        try:
            self.max_length = int(config_options["max_length"])
        except:
            raise RuntimeError("Required configuration field 'max_length' missing or not an integer")
        if not (self.max_length > 0):
            raise RuntimeError("'max_length' must be >= 1")
        if "path" in config_options:
            self.path = config_options["path"]

    def run_test(self):
        try:
            output = subprocess.check_output([os.path.join(self.path, "exiqgrep"), "-xc"])
            for line in output:
                matches = self.r.match(line)
                if matches:
                    count = int(matches.group("count"))
                    # total = int(matches.group("total"))
                    if count > self.max_length:
                        if count == 1:
                            self.record_fail("%d message queued" % count)
                        else:
                            self.record_fail("%d messages queued" % count)
                        return False
                    else:
                        if count == 1:
                            self.record_success("%d message queued" % count)
                        else:
                            self.record_success("%d messages queued" % count)
                        return True
            self.record_fail("Error getting queue size")
            return False
        except Exception, e:
            self.record_fail("Error running exiqgrep: %s" % e)
            return False

    def describe(self):
        return "Checking the exim queue length is < %d" % self.max_length

    def get_params(self):
        return (self.max_length, )


class MonitorWindowsDHCPScope(Monitor):
    """Checks a Windows DHCP scope to make sure it has sufficient free IPs in the pool."""

    # netsh dhcp server \\SERVER scope SCOPE show clients
    # "No of Clients(version N): N in the Scope

    type = "dhcpscope"
    max_used = 0
    scope = ""
    server = ""
    r = re.compile("No of Clients\(version \d+\): (?P<clients>\d+) in the Scope")

    def __init__(self, name, config_options):
        if not self.is_windows(True):
            raise RuntimeError("DHCPScope monitor requires a Windows platform.")
        Monitor.__init__(self, name, config_options)
        try:
            self.max_used = int(config_options["max_used"])
        except:
            raise RuntimeError("Required configuration field 'max_used' missing or not an integer")
        if not (self.max_used > 0):
            raise RuntimeError("max_used must be >= 1")

        try:
            self.scope = config_options["scope"]
        except:
            raise RuntimeError("Required configuration field 'scope' missing")

    def run_test(self):
        try:
            output = str(subprocess.check_output(["netsh", "dhcp", "server", "scope", self.scope, "show", "clients"]))
            matches = self.r.search(output)
            if matches:
                clients = int(matches.group("clients"))
                if clients > self.max_used:
                    self.record_fail("%d clients in scope" % clients)
                    return False
                else:
                    self.record_success("%d clients in scope" % clients)
                    return True
            self.record_fail("Error getting client count: no match")
            return False
        except Exception, e:
            print e
            self.record_fail("Error getting client count: %s", e)
            return False

    def describe(self):
        return "Checking the DHCP scope has fewer than %d leases" % self.max_used
