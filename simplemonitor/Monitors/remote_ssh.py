"""
Remote command via ssh to check for stuff without simplemonitor on the remote target

Input: 
 - command to execute
 - regex to extract the monitored value
 - expected value
 - logic to apply
"""

from venv import logger
from .monitor import Monitor, register
from enum import Enum
import paramiko
import re
from typing import Tuple, cast


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
        # ssh configuration
        self.command = cast(str, self.get_config_option("command", required=True))
        self.ssh_private_key_path = cast(str, self.get_config_option("ssh_private_key_path", required=True))
        self.ssh_username = cast(str, self.get_config_option("ssh_username", required=True))
        self.target_hostname = cast(str, self.get_config_option("target_hostname", required=True))
        self.target_port = cast(int, self.get_config_option("target_port", required=False, default="22"))
        # operator logic
        self.operator = cast(
            str,
            self.get_config_option(
                "operator",
                required=True,
                allowed_values=[Operator.EQUALS.value, Operator.GREATER_THAN.value, Operator.LESS_THAN.value, Operator.GREATER_THAN.value],
            ),
        )
        self.regex = re.compile(cast(str, self.get_config_option("regex", required=True)))
        # values to compare, cast to the expected type
        self.result_type = cast(
            str,
            self.get_config_option("result_type", required=True, allowed_values=[OperatorType.INTEGER.value, OperatorType.STRING.value]),
        )
        match self.result_type:
            case OperatorType.INTEGER.value:
                self.target_value = cast(int, self.get_config_option("target_value", required=True))
            case OperatorType.STRING.value:
                self.target_value = cast(str, self.get_config_option("target_value", required=True))

    def run_test(self) -> bool:
        # run remote command
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        try:
            client.connect(
                self.target_hostname,
                username=self.ssh_username,
                key_filename=self.ssh_private_key_path,
                port=self.target_port,
            )
        except TimeoutError:
            return self.record_fail(f"connection to {self.target_hostname} timed out")
        except ConnectionRefusedError:
            return self.record_fail(f"connection to {self.target_hostname} actively refused")
        else:
            _, stdout, _ = client.exec_command(self.command)

        # extract and cast the actual value
        command_result = stdout.read().decode("utf-8")  # let's hope for the best
        actual_value = re.match(self.regex, command_result).groups()[0]
        match self.result_type:
            case OperatorType.INTEGER.value:
                actual_value = cast(int, actual_value)
            case OperatorType.STRING.value:
                actual_value = cast(str, actual_value)

        # assess the comparison logic. str and int can be checked for equality, only int can be checked for greater/less than
        test_succeeded = False  # better be pessimistic
        match self.operator:
            case Operator.EQUALS.value:
                test_succeeded = actual_value == self.target_value
            case Operator.NOT_EQUALS.value:
                test_succeeded = actual_value != self.target_value
            case Operator.GREATER_THAN.value:
                test_succeeded = actual_value > self.target_value
            case Operator.LESS_THAN.value:
                test_succeeded = actual_value < self.target_value
        if self.result_type == OperatorType.STRING.value and (self.operator in [Operator.GREATER_THAN.value, Operator.LESS_THAN.value]):
            logger.warning(f"strings compared with '{self.operator}'")
        if test_succeeded:
            return self.record_success(f"it worked: {actual_value}")
        else:
            return self.record_fail(f"actual value: {actual_value} | operator: {self.operator} | target value: {self.target_value}")

    def get_params(self) -> Tuple:
        return (
            self.command,
            self.regex,
            self.target_value,
            self.operator,
            self.result_type,
            self.ssh_private_key_path,
            self.ssh_username,
            self.target_hostname,
        )

    def describe(self) -> str:
        return "run a remote command, extract its output and apply logic"
