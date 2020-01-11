# coding=utf-8
try:
    import syslog
except ImportError:
    pass

from ..Monitors.monitor import Monitor
from .alerter import Alerter, register


@register
class SyslogAlerter(Alerter):
    type = "syslog"

    def send_alert(self, name: str, monitor: Monitor) -> None:
        alert_type = self.should_alert(monitor)
        if alert_type == "failure":
            syslog.syslog(
                syslog.LOG_WARNING | syslog.LOG_USER,
                "Monitor %s failed %d times with message: %s"
                % (name, monitor.virtual_fail_count(), monitor.get_result()),
            )
