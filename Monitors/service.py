# coding=utf-8
import platform
import re
import os
import subprocess
import sys

from util import MonitorConfigurationError

from .monitor import Monitor


class MonitorSvc(Monitor):
    """Monitor a service handled by daemontools."""

    type = "svc"
    path = ""

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        self.path = Monitor.get_config_option(config_options, 'path', required=True)
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
        except Exception as e:
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
        self.service_name = Monitor.get_config_option(
            config_options,
            'service',
            required=True
        )
        self.want_state = Monitor.get_config_option(
            config_options,
            'state',
            default='RUNNING'
        )
        self.host = Monitor.get_config_option(
            config_options,
            'host',
            default='.'
        )

        if self.want_state not in ["RUNNING", "STOPPED"]:
            raise MonitorConfigurationError("invalid state {0} for MonitorService".format(self.want_state))

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
        except Exception as e:
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
        self.service_name = Monitor.get_config_option(config_options, 'service', required=True)
        self.script_path = Monitor.get_config_option(config_options, 'path', default='/usr/local/etc/rc.d')
        self.want_return_code = Monitor.get_config_option(config_options, 'return_code', required_type='int', default=0)
        if self.script_path.endswith("/"):
            self.script_path = self.script_path + self.service_name
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
        except subprocess.CalledProcessError as e:
            if e.returncode == self.want_return_code:
                self.record_success()
                return True
            returncode = -1
        except Exception as e:
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
        self.max_length = Monitor.get_config_option(config_options,
                                                    'max_length',
                                                    required_type='int',
                                                    minimum=1
                                                    )
        path = Monitor.get_config_option(config_options, 'path', default='/usr/local/sbin')
        self.path = os.path.join(path, "exiqgrep")

    def run_test(self):
        try:
            output = subprocess.check_output([self.path, "-xc"])
            output = output.decode('utf-8')
            for line in output.splitlines():
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
        except Exception as e:
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
        self.max_used = Monitor.get_config_option(config_options, 'max_used', required_type='int', minimum=1)
        self.scope = Monitor.get_config_option(config_options, 'scope', required=True)

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
        except Exception as e:
            self.record_fail("Error getting client count: {0}".format(e))
            return False

    def describe(self):
        return "Checking the DHCP scope has fewer than %d leases" % self.max_used
