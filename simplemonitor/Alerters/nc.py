try:
    import pync

    pync_available = True
except Exception:
    pync_available = False

import platform

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertType, register


@register
class NotificationCenterAlerter(Alerter):
    """Send alerts to the Mac OS X Notification Center."""

    _type = "nc"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        if not pync_available:
            self.alerter_logger.critical(
                "Pync package is not available, which is necessary to use NotificationCenterAlerter."
            )
            self.alerter_logger.critical("Try: pip install -r requirements.txt")
            self.alerter_logger.critical("     or pip install simplemonitor[nc]")
            self.available = False
            return

        if platform.system() != "Darwin":
            self.alerter_logger.critical(
                "This alerter (currently) only works on Mac OS X!"
            )
            self.available = False
            return

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Send the message."""

        alert_type = self.should_alert(monitor)
        message = ""

        if alert_type == AlertType.NONE:
            return
        elif alert_type == AlertType.FAILURE:
            message = "Monitor {} failed!".format(name)
        elif alert_type == AlertType.SUCCESS:
            message = "Monitor {} succeeded.".format(name)
        else:
            self.alerter_logger.error("Unknown alert type: {}".format(alert_type))
            return

        if not self._dry_run:
            pync.notify(message=message, title="SimpleMonitor")
        else:
            self.alerter_logger.info("dry_run: would send message: {}".format(message))
