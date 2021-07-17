"""
SimpleMonitor command execution as alerts
"""

import shlex
import subprocess  # nosec
from typing import Optional, cast

from ..Monitors.monitor import Monitor
from ..util import AlerterConfigurationError, format_datetime
from .alerter import Alerter, AlertType, register


@register
class ExecuteAlerter(Alerter):
    """Execute an external command when a monitor fails or recovers"""

    alerter_type = "execute"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)

        self.fail_command = cast(
            str, self.get_config_option("fail_command", allow_empty=False)
        )
        self.success_command = cast(
            str, self.get_config_option("success_command", allow_empty=False)
        )
        self.catchup_command = cast(
            str, self.get_config_option("catchup_command", allow_empty=False)
        )
        if (
            self.fail_command is None
            and self.success_command is None
            and self.catchup_command is None
        ):
            raise AlerterConfigurationError("execute alerter has no commands defined")

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Execute the command"""
        alert_type = self.should_alert(monitor)
        command = None  # type: Optional[str]
        downtime = monitor.get_downtime()
        if monitor.is_remote():
            host = monitor.running_on
        else:
            host = self.hostname

        if alert_type == AlertType.NONE:
            return
        if alert_type == AlertType.FAILURE:
            command = self.fail_command
        elif alert_type == AlertType.SUCCESS:
            command = self.success_command
        elif alert_type == AlertType.CATCHUP:
            if self.catchup_command == "fail_command":
                command = self.fail_command
        else:
            self.alerter_logger.error("Unknown alert type %s", alert_type)
            return

        if command is None:
            return

        command = command.format(
            hostname=host,
            name=name,
            days=downtime.days,
            hours=downtime.hours,
            minutes=downtime.minutes,
            seconds=downtime.seconds,
            failed_at=format_datetime(monitor.first_failure_time()),
            virtual_fail_count=monitor.virtual_fail_count(),
            info=monitor.get_result(),
            description=monitor.describe(),
            last_virtual_fail_count=monitor.last_virtual_fail_count(),
            failure_doc=monitor.failure_doc,
        )

        if not self._dry_run:
            self.alerter_logger.debug("About to execute command: %s", command)
            try:
                subprocess.call(shlex.split(command))  # nosec
                self.alerter_logger.debug("Command has finished.")
            except subprocess.SubprocessError:
                self.alerter_logger.exception(
                    "Exception encountered running command: %s", command
                )
        else:
            self.alerter_logger.info("Would run command: %s", command)

    def _describe_action(self) -> str:
        when = []
        if self.success_command:
            when.append("success")
        if self.fail_command:
            when.append("failure")
        if self.catchup_command:
            when.append("catchup")
        return "running command(s) on {when}".format(when=", ".join(when))
