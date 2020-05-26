try:
    import pync

    pync_available = True
except Exception:
    pync_available = False

import platform

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class NotificationCenterAlerter(Alerter):
    """Send alerts to the Mac OS X Notification Center."""

    alerter_type = "nc"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        if not pync_available:
            self.alerter_logger.critical(
                "Pync package is not available, which is necessary to use NotificationCenterAlerter."
            )
            self.alerter_logger.critical("Try: pip install -r requirements.txt")
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

        if alert_type not in [AlertType.FAILURE, AlertType.CATCHUP]:
            return
        message = self.build_message(AlertLength.NOTIFICATION, alert_type, monitor)

        if not self._dry_run:
            pync.notify(message=message, title="SimpleMonitor")
        else:
            self.alerter_logger.info("dry_run: would send message: %s", message)
