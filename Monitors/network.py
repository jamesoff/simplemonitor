# coding=utf-8
"""Network-related monitors for SimpleMonitor."""

import re
import sys
import socket
import datetime
import subprocess
import requests
from requests.auth import HTTPBasicAuth

from .monitor import Monitor


class MonitorHTTP(Monitor):
    """Check an HTTP server is working right.

    We can either check that we get a 200 OK back, or we can check for a regexp match in the page.
    """

    url = ""
    regexp = None
    regexp_text = ""
    allowed_codes = []

    type = "http"

    # optional - for HTTPS client authentication only
    certfile = None
    keyfile = None

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        self.url = Monitor.get_config_option(config_options, 'url', required=True)

        regexp = Monitor.get_config_option(config_options, 'regexp')
        if regexp is not None:
            self.regexp = re.compile(regexp)
            self.regexp_text = regexp
        if not regexp:
            self.allowed_codes = Monitor.get_config_option(
                config_options,
                'allowed_codes',
                default=[200],
                required_type='[int]'
            )
        else:
            self.allowed_codes = [200]

        # optionnal - for HTTPS client authentication only
        # in this case, certfile is required
        self.certfile = config_options.get('certfile')
        self.keyfile = config_options.get('keyfile')
        if self.certfile and not self.keyfile:
            self.keyfile = self.certfile
        if not self.certfile and self.keyfile:
            raise ValueError('config option keyfile is set but certfile is not')

        self.verify_hostname = Monitor.get_config_option(
            config_options,
            'verify_hostname',
            default=True,
            required_type='bool'
        )

        self.request_timeout = Monitor.get_config_option(
            config_options,
            'timeout',
            default=5,
            required_type='int'
        )

        self.username = config_options.get('username')
        self.password = config_options.get('password')

    def run_test(self):
        start_time = datetime.datetime.now()
        end_time = None
        try:
            if self.certfile is None and self.username is None:
                r = requests.get(self.url,
                                 timeout=self.request_timeout,
                                 verify=self.verify_hostname
                                 )
            elif self.certfile is None and self.username is not None:
                r = requests.get(self.url,
                                 timeout=self.request_timeout,
                                 auth=HTTPBasicAuth(
                                     self.username,
                                     self.password
                                 ),
                                 verify=self.verify_hostname
                                 )
            else:
                r = requests.get(self.url,
                                 timeout=self.request_timeout,
                                 cert=(self.certfile, self.keyfile),
                                 verify=self.verify_hostname
                                 )

            end_time = datetime.datetime.now()
            load_time = end_time - start_time
            if r.status_code not in self.allowed_codes:
                self.record_fail("Got status '{0} {1}' instead of {2}".format(r.status_code, r.reason, self.allowed_codes))
                return False
            if self.regexp is None:
                self.record_success("%s in %0.2fs" % (r.status_code, (load_time.seconds + (load_time.microseconds / 1000000.2))))
                return True
                matches = self.regexp.search(r.text)
                if matches:
                    self.record_success("%s in %0.2fs" % (r.status_code, (load_time.seconds + (load_time.microseconds / 1000000.2))))
                    return True
                self.record_fail("Got '{0} {1}' but couldn't match /{2}/ in page.".format(r.status_code, r.reason, self.regexp_text))
                return False
        except requests.exceptions.RequestException as e:
            self.record_fail("Requests exception while opening URL: {0}".format(e))
            return False
        except Exception as e:
            self.record_fail("Exception while trying to open url: {0}".format(e))
            return False

    def describe(self):
        """Explains what we do."""
        if self.regexp is None:
            message = "Checking that accessing %s returns HTTP/200 OK" % self.url
        else:
            message = "Checking that accessing %s returns HTTP/200 OK and that /%s/ matches the page" % (self.url, self.regexp_text)
        return message

    def get_params(self):
        return (self.url, self.regexp_text, self.allowed_codes)


class MonitorTCP(Monitor):
    """TCP port monitor"""

    host = ""
    port = ""
    type = "tcp"

    def __init__(self, name, config_options):
        """Constructor"""
        Monitor.__init__(self, name, config_options)
        self.host = Monitor.get_config_option(config_options, 'host', required=True)
        self.port = Monitor.get_config_option(
            config_options,
            'port',
            required=True,
            required_type='int',
            minimum=0
        )

    def run_test(self):
        """Check the port is open on the remote host"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(5.0)
            s.connect((self.host, self.port))
        except Exception:
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


class MonitorHost(Monitor):
    """Ping a host to make sure it's up"""

    host = ""
    ping_command = ""
    ping_regexp = ""
    type = "host"
    time_regexp = ""

    def __init__(self, name, config_options):
        """
        Note: We use -w/-t on Windows/POSIX to limit the amount of time we wait to 5 seconds.
        This is to stop ping holding things up too much. A machine that can't ping back in <5s is
        a machine in trouble anyway, so should probably count as a failure.
        """
        Monitor.__init__(self, name, config_options)
        ping_ttl = Monitor.get_config_option(
            config_options,
            'ping_ttl',
            required_type='int',
            minimum=0,
            default=5
        )
        ping_ms = str(ping_ttl * 1000)
        ping_ttl = str(ping_ttl)
        platform = sys.platform
        if platform in ['win32', 'cygwin']:
            self.ping_command = "ping -n 1 -w " + ping_ms + " %s"
            self.ping_regexp = 'Reply from [0-9a-f:.]+:.+time[=<]\d+ms'
            self.time_regexp = "Average = (?P<ms>\d+)ms"
        elif platform.startswith('freebsd') or platform.startswith('darwin'):
            self.ping_command = "ping -c1 -t" + ping_ttl + " %s"
            self.ping_regexp = "bytes from"
            self.time_regexp = "min/avg/max/stddev = [\d.]+/(?P<ms>[\d.]+)/"
        elif platform.startswith('linux'):
            self.ping_command = "ping -c1 -W" + ping_ttl + " %s"
            self.ping_regexp = "bytes from"
            self.time_regexp = "min/avg/max/stddev = [\d.]+/(?P<ms>[\d.]+)/"
        else:
            RuntimeError("Don't know how to run ping on this platform, help!")

        self.host = Monitor.get_config_option(
            config_options,
            'host',
            required=True
        )

    def run_test(self):
        r = re.compile(self.ping_regexp)
        r2 = re.compile(self.time_regexp)
        success = False
        pingtime = 0.0
        try:
            cmd = (self.ping_command % self.host).split(' ')
            output = subprocess.check_output(cmd)
            for line in str(output).split("\n"):
                matches = r.search(line)
                if matches:
                    success = True
                else:
                    matches = r2.search(line)
                    if matches:
                        pingtime = matches.group("ms")
        except Exception as e:
            self.record_fail(e)
            return False
        if success:
            if pingtime > 0:
                self.record_success("%sms" % pingtime)
            else:
                self.record_success()
            return True
        self.record_fail()
        return False

    def describe(self):
        """Explains what this instance is checking"""
        return "checking host %s is pingable" % self.host

    def get_params(self):
        return (self.host, )


class MonitorDNS(Monitor):
    """Monitor DNS server."""

    type = 'dns'
    path = ''
    command = 'dig'

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        self.path = Monitor.get_config_option(
            config_options,
            'record',
            required=True
        )

        self.desired_val = Monitor.get_config_option(config_options, 'desired_val')

        self.server = Monitor.get_config_option(config_options, 'server')

        self.params = [self.command]

        if self.server:
            self.params.append("@%s" % self.server)

        self.rectype = Monitor.get_config_option(config_options, 'record_type')
        if self.rectype:
            self.params.append('-t')
            self.params.append(config_options['record_type'])

        self.params.append(self.path)
        self.params.append('+short')

    def run_test(self):
        try:
            result = subprocess.check_output(self.params).decode('utf-8')
            result = result.strip()
            if result is None or result == '':
                return self.record_fail("failed to resolve %s" % self.path)
            if self.desired_val and result != self.desired_val:
                return self.record_fail("resolved DNS record is unexpected: %s != %s" % (self.desired_val, result))
            return self.record_success()
        except subprocess.CalledProcessError as e:
            return self.record_fail("Command '%s' exited non-zero (%d)" % (
                ' '.join(self.params),
                e.returncode
            ))
        except Exception as e:
            return self.record_fail("Exception while executing '%s': %s" % (' '.join(self.params), e))

    def describe(self):
        if self.desired_val:
            end_part = "resolves to %s" % self.desired_val
        else:
            end_part = "is resolvable"

        if self.rectype:
            mid_part = "%s record %s" % (self.rectype, self.path)
        else:
            mid_part = "record %s" % self.path

        if self.server:
            very_end_part = " at %s" % self.server
        else:
            very_end_part = ''
        return "Checking that DNS %s %s%s" % (mid_part, end_part, very_end_part)

    def get_params(self):
        return (self.path, )
