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

        type = self.should_alert(monitor)

        if type == "":
            return
        elif type == "failure":
            pync.notify('Monitor failed!', title="SimpleMonitor -{}".format(name))
        else:
            pass