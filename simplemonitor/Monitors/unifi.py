"""
UniFi monitoring for SimpleMonitor
"""

import re
from typing import Dict, NoReturn, Union, cast

from paramiko.client import RejectPolicy, SSHClient
from paramiko.ssh_exception import SSHException

from .monitor import Monitor, register


@register
class MonitorUnifiFailover(Monitor):
    """Monitor USG WAN Failover"""

    monitor_type = "unifi_failover"

    def __init__(self, name: str, config_options: dict) -> None:
        if "gap" not in config_options:
            config_options["gap"] = 300  # 5 mins
        super().__init__(name, config_options)
        self._router_address = cast(
            str, self.get_config_option("router_address", required=True)
        )
        self._username = cast(
            str, self.get_config_option("router_username", required=True)
        )
        self._password = self.get_config_option("router_password", required=False)
        self._ssh_key = self.get_config_option("ssh_key", required=False)
        if self._ssh_key is None and self._password is None:
            raise ValueError("must specify only one of router_password or ssh_key")
        self._check_interface = cast(
            str, self.get_config_option("check_interface", default="eth2")
        )

    def run_test(self) -> Union[NoReturn, bool]:
        try:
            with SSHClient() as client:
                client.set_missing_host_key_policy(RejectPolicy)
                client.load_system_host_keys()
                client.connect(
                    hostname=self._router_address,
                    username=self._username,
                    password=self._password,
                    key_filename=self._ssh_key,
                )
                _, stdout, _ = client.exec_command(  # nosec
                    "sudo /usr/sbin/ubnt-hal wlbGetStatus"
                )
                data = {}  # type: Dict[str, Dict[str, str]]
                data_block = {}  # type: Dict[str, str]
                interface = ""
                for _line in stdout.readlines():
                    line = _line.strip()
                    matches = re.match(r"interface +: (\w+)", line)
                    if matches:
                        if interface != "" and len(data_block) > 0:
                            data[interface] = data_block
                            data_block = {}
                        interface = matches.group(1)
                        data_block = {}
                        continue
                    matches = re.match(r"carrier +: (\w+)", line)
                    if matches:
                        data_block["carrier"] = matches.group(1)
                        continue
                    matches = re.match(r"status +: (\w+)", line)
                    if matches:
                        data_block["status"] = matches.group(1)
                        continue
                    matches = re.match(r"gateway +: (\w+)", line)
                    if matches:
                        data_block["gateway"] = matches.group(1)
                if interface != "" and len(data_block) > 0:
                    data[interface] = data_block
        except SSHException as error:
            self.monitor_logger.exception("Failed to ssh to USG")
            return self.record_fail("Failed to ssh to USG: {}".format(error))
        if self._check_interface not in data:
            self.monitor_logger.debug("processed data was %s", data)
            return self.record_fail(
                "Could not get status for interface {}".format(self._check_interface)
            )
        if data[self._check_interface]["carrier"] != "up":
            return self.record_fail(
                "Interface {} carrier is in status {} (wanted 'up')".format(
                    self._check_interface, data[self._check_interface]["carrier"]
                )
            )
        if data[self._check_interface]["status"] != "failover":
            return self.record_fail(
                "Interface {} is in status {} (wanted 'failover')".format(
                    self._check_interface, data[self._check_interface]["status"]
                )
            )
        if data[self._check_interface]["gateway"] == "unknown":
            return self.record_fail(
                "Interface {} has gateway {}".format(
                    self._check_interface, data[self._check_interface]["gateway"]
                )
            )
        return self.record_success(
            "Interface {} is {} with status {}".format(
                self._check_interface,
                data[self._check_interface]["carrier"],
                data[self._check_interface]["status"],
            )
        )

    def describe(self) -> str:
        return "Checking USG at {} has interface {} up and not failed over".format(
            self._router_address, self._check_interface
        )


@register
class MonitorUnifiFailoverWatchdog(Monitor):
    """Monitor UniFi WAN watchdog"""

    monitor_type = "unifi_watchdog"

    def __init__(self, name: str, config_options: dict) -> None:
        if "gap" not in config_options:
            config_options["gap"] = 300  # 5 mins
        super().__init__(name, config_options)
        self._router_address = cast(
            str, self.get_config_option("router_address", required=True)
        )
        self._username = cast(
            str, self.get_config_option("router_username", required=True)
        )
        self._password = self.get_config_option("router_password", required=False)
        self._ssh_key = self.get_config_option("ssh_key", required=False)
        if self._ssh_key is None and self._password is None:
            raise ValueError("must specify only one of router_password or ssh_key")
        self._primary_interface = cast(
            str, self.get_config_option("primary_interface", default="pppoe0")
        )
        self._secondary_interface = cast(
            str, self.get_config_option("secondary_interface", default="eth2")
        )

    def run_test(self) -> Union[NoReturn, bool]:
        try:
            with SSHClient() as client:
                client.set_missing_host_key_policy(RejectPolicy)
                client.load_system_host_keys()
                client.connect(
                    hostname=self._router_address,
                    username=self._username,
                    password=self._password,
                    key_filename=self._ssh_key,
                )
                _, stdout, _ = client.exec_command(  # nosec
                    "/usr/sbin/ubnt-hal wlbGetWdStatus"
                )
                data = {}  # type: Dict[str, Dict[str, str]]
                data_block = {}  # type: Dict[str, str]
                interface = ""
                for _line in stdout.readlines():
                    line = _line.strip()
                    matches = re.match(
                        r"([a-z]+[0-9])", line
                    )  # two spaces and an if name
                    if matches:
                        if interface != "" and len(data_block) > 0:
                            data[interface] = data_block
                            data_block = {}
                        interface = matches.group(1)
                        data_block = {}
                        continue
                    matches = re.match(r"status: (\w+)", line)
                    if matches:
                        data_block["status"] = matches.group(1)
                        continue
                    matches = re.match(r"ping gateway: ([^ ]+) - (\w+)", line)
                    if matches:
                        data_block["gateway"] = matches.group(1)
                        data_block["ping_status"] = matches.group(2)
                        continue
                if interface != "" and len(data_block) > 0:
                    data[interface] = data_block
        except SSHException as error:
            self.monitor_logger.exception("Failed to ssh to USG")
            return self.record_fail("Failed to ssh to USG: {}".format(error))
        for interface in [self._primary_interface, self._secondary_interface]:
            if interface not in data:
                self.monitor_logger.debug("processed data was %s", data)
                return self.record_fail(
                    "Could not get status for interface {}".format(interface)
                )
            if data[interface]["status"] != "Running":
                return self.record_fail(
                    "Interface {} in status {} (wanted 'Running')".format(
                        interface, data[interface]["status"]
                    )
                )
            if data[interface]["ping_status"] != "REACHABLE":
                return self.record_fail(
                    "Interface {} ping ({}) is {} (wanted 'REACHABLE')".format(
                        interface,
                        data[interface]["gateway"],
                        data[interface]["ping_status"],
                    )
                )
        return self.record_success(
            "Interfaces {} and {} both running and pinging".format(
                self._primary_interface, self._secondary_interface
            )
        )

    def describe(self) -> str:
        return "Checking USG at {} has interface {} and {} running and pinging".format(
            self._router_address, self._primary_interface, self._secondary_interface
        )
