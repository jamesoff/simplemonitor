try:
    import pync
    pync_available = True
except ImportError:
    pync_available = False

from .alerter import Alerter

class NotificationCenterAlerter(Alerter):
    """Send alerts to the Mac OS X Notification Center."""

    def __init__(self, config_options):
        Alerter.__init__(self, config_options)
        if not pync_available:
            self.alerter_logger.critical("Pync package is not available, cannot use NotificationCenterAlerter.")
            self.alerter_logger.critical("Try: pip install -r requirements.txt")
            return

    def send_alert(self, name, monitor):
        """Send the message."""

        alert_type = self.should_alert(monitor)
        message = ""

        if alert_type == "":
            return
        elif alert_type == "failure":
            message = "Monitor {} failed!".format(name)
        elif alert_type == "success":
            message = "Monitor {} succeeded.".format(name)
        else:
            self.alerter_logger.error("Unknown alert type: {}".format(alert_type))
            return

        if not self.dry_run:
            pync.notify(message=message, title="SimpleMonitor")
        else:
            self.alerter_logger.info("dry_run: would send message: {}".format(message))
