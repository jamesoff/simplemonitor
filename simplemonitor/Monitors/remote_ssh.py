"""
Remote command via ssh to check for stuff without simplemonitor on the remote target

Input:
 - command to execute
 - regex to extract the monitored value
 - expected value
 - logic to apply
"""

import re
from enum import Enum
from typing import Tuple, cast

import paramiko

from .monitor import Monitor, register


class Operator(Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"


class OperatorType(Enum):
    STRING = "str"
    INTEGER = "int"


@register
class MonitorRemoteSSH(Monitor):
    monitor_type = "remote_ssh"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        # description
        self.description = cast(
            str, self.get_config_option("description", required=False)
        )  # maybe define default here instead of a try: ?
        self.success_message = cast(
            str,
            self.get_config_option(
                "success_message", required=False, default="it worked"
            ),
        )
        # ssh configuration
        self.command = cast(str, self.get_config_option("command", required=True))
        self.ssh_private_key_path = cast(
            str, self.get_config_option("ssh_private_key_path", required=True)
        )
        self.ssh_username = cast(
            str, self.get_config_option("ssh_username", required=True)
        )
        self.target_hostname = cast(
            str, self.get_config_option("target_hostname", required=True)
        )
        self.target_port = cast(
            int, self.get_config_option("target_port", required=False, default="22")
        )
        # operator logic
        self.operator = cast(
            str,
            self.get_config_option(
                "operator",
                required=True,
                allowed_values=[
                    Operator.EQUALS.value,
                    Operator.NOT_EQUALS.value,
                    Operator.LESS_THAN.value,
                    Operator.GREATER_THAN.value,
                ],
            ),
        )
        self.regex = re.compile(
            cast(str, self.get_config_option("regex", required=True))
        )
        # values to compare, cast to the expected type
        self.result_type = cast(
            str,
            self.get_config_option(
                "result_type",
                required=True,
                allowed_values=[OperatorType.INTEGER.value, OperatorType.STRING.value],
            ),
        )
        self.target_value: str | int
        match self.result_type:
            case OperatorType.INTEGER.value:
                self.target_value = cast(
                    int, self.get_config_option("target_value", required=True)
                )
            case OperatorType.STRING.value:
                self.target_value = cast(
                    str, self.get_config_option("target_value", required=True)
                )

    def run_test(self) -> bool:
        # run remote command
        with paramiko.SSHClient() as client:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
            try:
                client.connect(
                    self.target_hostname,
                    username=self.ssh_username,
                    key_filename=self.ssh_private_key_path,
                    port=self.target_port,
                )
            except TimeoutError:
                return self.record_fail(
                    f"connection to {self.target_hostname} timed out"
                )
            except ConnectionRefusedError:
                return self.record_fail(
                    f"connection to {self.target_hostname} actively refused"
                )
            except paramiko.SSHException as e:
                return self.record_fail(
                    f"connection to {self.target_hostname} failed: {e}"
                )
            else:
                _, stdout, _ = client.exec_command(self.command)
            # extract and cast the actual value
            try:
                # let's hope for the best
                command_result = stdout.read().decode("utf-8")
            except Exception as e:
                return self.record_fail(
                    f"cannot decode the output of the ssh command: {e}"
                )
        if matches := re.match(self.regex, command_result):
            matched_value = matches.groups()[0]
        else:
            return self.record_fail("Failed to match regex to command output")
        actual_value: str | int
        match self.result_type:
            case OperatorType.INTEGER.value:
                actual_value = int(matched_value)
            case OperatorType.STRING.value:
                actual_value = str(matched_value)
            case _:
                raise RuntimeError("misconfiguration for operator type")

        # assess the comparison logic.
        # str and int can be checked for equality,
        # but only int can be checked for greater/less than
        test_succeeded = False  # better be pessimistic
        match self.operator:
            case Operator.EQUALS.value:
                test_succeeded = actual_value == self.target_value
            case Operator.NOT_EQUALS.value:
                test_succeeded = actual_value != self.target_value
            case Operator.GREATER_THAN.value if isinstance(
                actual_value, int
            ) and isinstance(self.target_value, int):
                test_succeeded = actual_value > self.target_value
            case Operator.LESS_THAN.value if isinstance(
                actual_value, int
            ) and isinstance(self.target_value, int):
                test_succeeded = actual_value < self.target_value
        if test_succeeded:
            return self.record_success(self.success_message.format(actual_value))
        else:
            return self.record_fail(
                f"actual value: {actual_value} | operator: {self.operator} | target value: {self.target_value}"
            )

    def get_params(self) -> Tuple:
        return (
            self.command,
            self.description,
            self.success_message,
            self.regex,
            self.target_value,
            self.operator,
            self.result_type,
            self.ssh_private_key_path,
            self.ssh_username,
            self.target_hostname,
            self.target_port,
        )

    def describe(self) -> str:
        try:
            return self.description
        except AttributeError:
            return "run a remote command, extract its output and apply logic"
