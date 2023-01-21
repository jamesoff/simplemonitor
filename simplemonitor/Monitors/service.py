"""
Service monitoring for SimpleMonitor
"""

import fnmatch
import os
import platform
import re
import subprocess
import time
from typing import Any, List, Optional, Tuple, cast

import psutil

from .monitor import Monitor, register

try:
    import pydbus
except ImportError:
    pydbus = None


@register
class MonitorSvc(Monitor):
    """Monitor a service handled by daemontools."""

    monitor_type = "svc"
    path = ""

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self.path = cast(str, self.get_config_option("path", required=True))
        self.params = ("svok %s" % self.path).split(" ")

    def run_test(self) -> bool:
        if self.path == "":
            return self.record_fail("Path is not configured")
        try:
            result = subprocess.call(self.params)
            if result is None:
                result = 0
            if result > 0:
                return self.record_fail("svok returned %d" % int(result))
            return self.record_success()
        except Exception as error:
            return self.record_fail("Exception while executing svok: %s" % error)

    def describe(self) -> str:
        return (
            "Checking that the supervise-managed service in %s is running." % self.path
        )

    def get_params(self) -> Tuple:
        return (self.path,)


@register
class MonitorService(Monitor):
    """Monitor a Windows service"""

    service_name = ""
    want_state = "RUNNING"
    host = "."
    monitor_type = "service"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        if psutil is None:
            self.monitor_logger.critical("psutil is not installed.")
            self.monitor_logger.critical("Try: pip install -r requirements.txt")
        self.service_name = cast(str, self.get_config_option("service", required=True))
        self.want_state = cast(
            str,
            self.get_config_option(
                "state",
                default="RUNNING",
                allowed_values=[
                    "RUNNING",
                    "STOPPED",
                    "PAUSED",
                    "START_PENDING",
                    "PAUSE_PENDING",
                    "CONTINUE_PENDING",
                    "STOP_PENDING",
                ],
            ),
        )
        self.host = cast(str, self.get_config_option("host", default="."))

    def run_test(self) -> bool:
        """Check the service is in the desired state"""
        if psutil is None:
            return self.record_fail("psutil is not installed")
        try:
            service = psutil.win_service_get(self.service_name)
        except psutil.NoSuchProcess:
            return self.record_fail(
                "service {} does not exist".format(self.service_name)
            )
        except AttributeError:
            return self.record_fail("not supported on this platform")
        except Exception:
            self.monitor_logger.exception("Failed to get service")
            return self.record_fail("Unable to get service")

        _state = service.status()
        if _state:
            state = _state.upper()
        else:
            state = "NONE"
        if state != self.want_state:
            return self.record_fail(
                "Service state is {} (wanted {})".format(state, self.want_state)
            )
        return self.record_success()

    def describe(self) -> str:
        """Explains what this instance is checking"""
        return "checking for service called %s in state %s" % (
            self.service_name,
            self.want_state,
        )

    def get_params(self) -> Tuple:
        return (self.host, self.service_name, self.want_state)


@register
class MonitorRC(Monitor):
    """Monitor a service handled by an rc.d script.

    This monitor checks the return code of /usr/local/etc/rc.d/<name>
    and reports failure if it's non-zero by default.
    """

    monitor_type = "rc"

    def __init__(self, name: str, config_options: dict) -> None:
        """Initialise the class.
        Change script path to /etc/rc.d/ to monitor base system services. If the
        script path ends with /, the service name is appended."""
        super().__init__(name, config_options)
        self.service_name = cast(str, self.get_config_option("service", required=True))
        self.script_path = cast(
            str, self.get_config_option("path", default="/usr/local/etc/rc.d/")
        )
        self.want_return_code = cast(
            str, self.get_config_option("return_code", required_type="int", default=0)
        )
        if self.script_path.endswith("/"):
            self.script_path = self.script_path + self.service_name
        if not os.path.isfile(self.script_path):
            if os.path.isfile(self.script_path + ".sh"):
                self.script_path = self.script_path + ".sh"
            else:
                raise RuntimeError("Script %s(.sh) does not exist" % self.script_path)

    def run_test(self) -> bool:
        """Check the service is in the desired state."""
        if platform.system() in ["Microsoft", "CYGWIN_NT-6.0"]:
            return self.record_fail("Cannot run this monitor on a non-UNIX host.")
        try:
            returncode = subprocess.check_call([self.script_path, "status"])
            if returncode == self.want_return_code:
                return self.record_success()
        except subprocess.CalledProcessError as error:
            if error.returncode == self.want_return_code:
                return self.record_success()
            returncode = -1
        except Exception as error:
            return self.record_fail("Exception while executing script: %s" % error)
        return self.record_fail(
            "Return code: %d (wanted %d)" % (returncode, int(self.want_return_code))
        )

    def get_params(self) -> Tuple:
        return (self.service_name, self.want_return_code)

    def describe(self) -> str:
        """Explains what this instance is checking."""
        return "Checks service %s is running" % self.script_path


@register
class MonitorUnixService(Monitor):
    """Monitor a service handled by a generic "service" command.

    If "service X status" exits 0 for the service being up, and non-zero
    otherwise, this is for you.
    """

    monitor_type = "unix_service"

    def __init__(
        self, name: str = "unnamed", config_options: Optional[dict] = None
    ) -> None:
        super().__init__(name=name, config_options=config_options)
        self.service_name = cast(str, self.get_config_option("service", required=True))
        self.want_state = cast(
            str,
            self.get_config_option(
                "state", allowed_values=["running", "stopped"], default="running"
            ),
        )
        if self.want_state == "running":
            self._want_return_code = 0
        else:
            self._want_return_code = 1

    def run_test(self) -> bool:
        try:
            result = subprocess.run(
                ["service", self.service_name, "status"],
                check=False,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )  # nosec
            returncode = result.returncode
        except subprocess.SubprocessError as exception:
            return self.record_fail(
                "Failed to run 'service {} status: {}".format(
                    self.service_name, exception
                )
            )
        if returncode == self._want_return_code:
            return self.record_success()
        return self.record_fail(
            "Got exit code {}, wanted {}".format(returncode, self._want_return_code)
        )

    def get_params(self) -> Tuple:
        return (self.service_name, self.want_state)

    def describe(self) -> str:
        return "Checking service {} is {}".format(self.service_name, self.want_state)


@register
class MonitorSystemdUnit(Monitor):
    """Monitor a systemd unit.

    This monitor checks the state of the unit as given by
    /org/freedesktop/systemd1/ListUnits
    and reports failure if it is not one of the expected states.
    """

    monitor_type = "systemd-unit"

    # A cached shared by all instances of MonitorSystemdUnit, so a single
    # call is done for all monitors at once.
    _listunit_cache = []  # type: List[Any]
    _listunit_cache_expiry = 0
    CACHE_LIFETIME = 1  # in seconds

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        if not pydbus:
            self.monitor_logger.critical(
                "pydbus package is not available, cannot use MonitorSystemdUnit."
            )
            return
        self.unit_name = cast(str, self.get_config_option("name", required=True))
        self.want_load_states = cast(
            List[str],
            self.get_config_option(
                "load_states", required_type="[str]", default=["loaded"]
            ),
        )
        self.want_active_states = cast(
            List[str],
            self.get_config_option(
                "active_states", required_type="[str]", default=["active", "reloading"]
            ),
        )
        self.want_sub_states = cast(
            List[str],
            self.get_config_option("sub_states", required_type="[str]", default=[]),
        )

    @classmethod
    def _list_units(cls) -> List[Any]:
        if pydbus is None:
            raise RuntimeError("pydbus module not installed")
        if cls._listunit_cache_expiry < time.time():
            bus = pydbus.SystemBus()
            systemd = bus.get(".systemd1")
            cls._listunit_cache_expiry = int(time.time()) + cls.CACHE_LIFETIME
            cls._listunit_cache = list(systemd.ListUnits())
        return cls._listunit_cache

    def run_test(self) -> bool:
        """Check the service is in the desired state."""
        nb_matches = 0
        for unit in self._list_units():
            (
                name,
                desc,
                load_state,
                active_state,
                sub_state,
                follower,
                unit_path,
                job_id,
                job_type,
                job_path,
            ) = unit
            if fnmatch.fnmatch(name, self.unit_name):
                result = self._check_unit(name, load_state, active_state, sub_state)
                nb_matches += 1
                # TODO: is this right?
                return result
        return self.record_fail("No unit %s" % self.unit_name)

    def _check_unit(
        self, name: str, load_state: str, active_state: str, sub_state: str
    ) -> bool:
        if self.want_load_states and load_state not in self.want_load_states:
            return self.record_fail(
                "Unit {0} has load state: {1} (wanted {2})".format(
                    name, load_state, self.want_load_states
                )
            )
        if self.want_active_states and active_state not in self.want_active_states:
            return self.record_fail(
                "Unit {0} has active state: {1} (wanted {2})".format(
                    name, active_state, self.want_active_states
                )
            )
        if self.want_sub_states and sub_state not in self.want_sub_states:
            return self.record_fail(
                "Unit {0} has sub state: {1} (wanted {2})".format(
                    name, sub_state, self.want_sub_states
                )
            )
        # TODO: added since there's no other apparent path to success
        return self.record_success("Implicit success for unit {0}".format(name))

    def get_params(self) -> Tuple:
        return (
            self.unit_name,
            self.want_load_states,
            self.want_active_states,
            self.want_sub_states,
        )

    def describe(self) -> str:
        return "Checks unit %s is running" % self.name


@register
class MonitorProcess(Monitor):
    """Check for a running process."""

    monitor_type = "process"

    def __init__(
        self, name: str = "unnamed", config_options: Optional[dict] = None
    ) -> None:
        if config_options is None:
            config_options = {}
        super().__init__(name=name, config_options=config_options)
        if psutil is None:
            self.monitor_logger.critical("psutil is not installed.")
            self.monitor_logger.critical("Try: pip install -r requirements.txt")
        self.process_name = cast(
            str, self.get_config_option("process_name", required=True)
        )
        self.max_count = cast(
            int, self.get_config_option("max_count", required_type="int", default=-1)
        )
        self.min_count = cast(
            int, self.get_config_option("min_count", required_type="int", default=1)
        )
        self.username = cast(
            Optional[str], self.get_config_option("username", required_type="str")
        )

    @staticmethod
    def _find_process_by_name(
        name: str, username: Optional[str] = None
    ) -> List[psutil.Process]:
        processes = []
        for process in psutil.process_iter(["name", "exe", "cmdline", "username"]):
            if (
                name == process.info["name"]
                or (
                    process.info["exe"]
                    and os.path.basename(process.info["exe"]) == name
                )
                or (process.info["cmdline"] and process.info["cmdline"][0] == name)
            ):
                if username is None or username == process.info["username"]:
                    processes.append(process)
        return processes

    def run_test(self) -> bool:
        if psutil is None:
            return self.record_fail("psutil is not installed")
        processes = self._find_process_by_name(self.process_name, self.username)
        count = len(processes)
        if count == 1:
            message = "1 matching process running"
        else:
            message = "{} matching processes running".format(count)
        if count < self.min_count:
            return self.record_fail(message)
        if self.max_count > -1 and count > self.max_count:
            return self.record_fail(message)
        return self.record_success(message)

    def get_params(self) -> Tuple:
        return (self.process_name, self.min_count, self.max_count, self.username)

    def describe(self) -> str:
        desc = "Checking for at least {} and at most {} processes matching {}".format(
            self.min_count,
            "infinity" if self.max_count == -1 else self.max_count,
            self.process_name,
        )
        if self.username:
            desc = desc + " owned by {}".format(self.username)
        return desc


@register
class MonitorEximQueue(Monitor):
    """Make sure an exim queue isn't too big."""

    monitor_type = "eximqueue"
    max_length = 10
    r = re.compile(r"(?P<count>\d+) matches out of (?P<total>\d+) messages")
    path = "/usr/local/sbin"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self.max_length = self.get_config_option(
            "max_length", required_type="int", minimum=1
        )
        path = self.get_config_option("path", default="/usr/local/sbin")
        self.path = os.path.join(path, "exiqgrep")

    def run_test(self) -> bool:
        try:
            _output = subprocess.check_output([self.path, "-xc"])
            output = _output.decode("utf-8")
            for line in output.splitlines():
                matches = self.r.match(line)
                if matches:
                    count = int(matches.group("count"))
                    # total = int(matches.group("total"))
                    if count > self.max_length:
                        if count == 1:
                            return self.record_fail("%d message queued" % count)
                        return self.record_fail("%d messages queued" % count)
                    if count == 1:
                        return self.record_success("%d message queued" % count)
                    return self.record_success("%d messages queued" % count)
            return self.record_fail("Error getting queue size")
        except Exception as error:
            return self.record_fail("Error running exiqgrep: %s" % error)

    def describe(self) -> str:
        return "Checking the exim queue length is < %d" % self.max_length

    def get_params(self) -> Tuple:
        return (self.max_length,)


@register
class MonitorWindowsDHCPScope(Monitor):
    """Checks a Windows DHCP scope to make sure it has sufficient free IPs in the pool."""

    # netsh dhcp server \\SERVER scope SCOPE show clients
    # "No of Clients(version N): N in the Scope

    monitor_type = "dhcpscope"
    max_used = 0
    scope = ""
    server = ""
    r = re.compile(r"No of Clients\(version \d+\): (?P<clients>\d+) in the Scope")

    def __init__(self, name: str, config_options: dict) -> None:
        if not self.is_windows(True):
            raise RuntimeError("DHCPScope monitor requires a Windows platform.")
        super().__init__(name, config_options)
        self.max_used = self.get_config_option(
            "max_used", required_type="int", minimum=1
        )
        self.scope = self.get_config_option("scope", required=True)

    def run_test(self) -> bool:
        try:
            output = str(
                subprocess.check_output(
                    ["netsh", "dhcp", "server", "scope", self.scope, "show", "clients"]
                )
            )
            matches = self.r.search(output)
            if matches:
                clients = int(matches.group("clients"))
                if clients > self.max_used:
                    return self.record_fail("%d clients in scope" % clients)
                return self.record_success("%d clients in scope" % clients)
            return self.record_fail("Error getting client count: no match")
        except Exception as error:
            return self.record_fail("Error getting client count: {0}".format(error))

    def describe(self) -> str:
        return "Checking the DHCP scope has fewer than %d leases" % self.max_used
