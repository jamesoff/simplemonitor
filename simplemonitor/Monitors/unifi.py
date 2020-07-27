import re
from typing import Dict, NoReturn, Union, cast

from .monitor import Monitor, register

try:
    from paramiko.client import SSHClient, RejectPolicy
    from paramiko.ssh_exception import SSHException

    ssh2_available = True
except ImportError:
    ssh2_available = False


@register
class MonitorUnifiFailover(Monitor):

    monitor_type = "unifi_failover"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self._router_address = cast(
            str, self.get_config_option("router_address", required=True)
        )
        self._username = cast(
            str, self.get_config_option("router_username", required=True)
        )
        self._password = cast(
            str, self.get_config_option("router_password", required=False, default="")
        )
        self._ssh_key = cast(
            str, self.get_config_option("ssh_key", required=False, default="")
        )
        if self._ssh_key != "" and self._password != "":
            raise ValueError("must specify only one of router_password or ssh_key")
        self._check_interface = cast(
            str, self.get_config_option("check_interface", default="eth2")
        )

    def run_test(self) -> Union[NoReturn, bool]:
        if not ssh2_available:
            return self.record_fail("ssh2_python library is not installed")

        try:
            with SSHClient() as client:
                client.set_missing_host_key_policy(RejectPolicy)
                client.connect(
                    hostname=self._router_address,
                    username=self._username,
                    password=self._password,
                    key_filename=self._ssh_key,
                )
                _, stdout, _ = client.exec_command(
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
                "Interface {} is not in status {} (wanted 'failover')".format(
                    self._check_interface, data[self._check_interface]["status"]
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
