"""
SimpleMonitor alerts via macOS Notification Center
"""

import platform

try:
    import macos

    PYMACOS_AVAILABLE = True
except ImportError:
    PYMACOS_AVAILABLE = False

from ..Monitors.monitor import Monitor
from .alerter import Alerter, AlertLength, AlertType, register


@register
class NotificationCenterAlerter(Alerter):
    """Send alerts to the macOS Notification Center"""

    alerter_type = "nc"

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)
        if platform.system() != "Darwin" or not PYMACOS_AVAILABLE:
            self.alerter_logger.critical(
                "This alerter (currently) only works on Mac OS X!"
            )
            return

    def send_alert(self, name: str, monitor: Monitor) -> None:
        """Send the message"""
        if not PYMACOS_AVAILABLE:
            self.alerter_logger.critical("Missing pymacos package")
            return
        alert_type = self.should_alert(monitor)
        message = ""

        if alert_type not in [AlertType.FAILURE, AlertType.CATCHUP]:
            return
        message = self.build_message(AlertLength.NOTIFICATION, alert_type, monitor)

        if not self._dry_run:
            try:
                macos.notify(message, title="SimpleMonitor")
            except Exception:
                # Includes notifications being turned off, which macOS would
                # otherwise drop without a word.
                self.alerter_logger.exception("Couldn't send notification")
        else:
            self.alerter_logger.info("dry_run: would send message: %s", message)

    def _describe_action(self) -> str:
        return "sending notifications via Notification Center"
