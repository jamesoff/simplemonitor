"""
SimpleMonitor alerts into syslog
"""

try:
    import syslog

    SYSLOG_AVAILABLE = True
except ImportError:
    SYSLOG_AVAILABLE = False

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertType, register


@register
class SyslogAlerter(Alerter):
    """Send alerts to syslog"""

    alerter_type = "syslog"

    def send_alert(self, name: str, monitor: Monitor) -> None:
        if not SYSLOG_AVAILABLE:
            self.alerter_logger.critical("syslog not available")
            return
        alert_type = self.should_alert(monitor)
        if alert_type == AlertType.FAILURE:
            syslog.syslog(
                syslog.LOG_WARNING | syslog.LOG_USER,
                "Monitor %s failed %d times with message: %s"
                % (name, monitor.virtual_fail_count(), monitor.get_result()),
            )

    def _describe_action(self) -> str:
        return "writing messages to syslog"
