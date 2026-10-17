from unittest import TestCase, mock

from simplemonitor.Alerters import nc
from simplemonitor.Monitors import monitor


@mock.patch.object(nc, "PYMACOS_AVAILABLE", True)
@mock.patch("platform.system", return_value="Darwin")
class TestNotificationCenterAlerter(TestCase):
    def failed_monitor(self):
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        return m

    def test_failure_is_notified(self, _system):
        with mock.patch.object(nc, "macos", create=True) as macos:
            a = nc.NotificationCenterAlerter({})
            a.send_alert("fail", self.failed_monitor())

        macos.notify.assert_called_once()
        args, kwargs = macos.notify.call_args
        self.assertIn("fail", args[0])
        self.assertEqual(kwargs, {"title": "SimpleMonitor"})

    def test_notification_error_is_logged_not_raised(self, _system):
        with mock.patch.object(nc, "macos", create=True) as macos:
            macos.notify.side_effect = PermissionError("notifications are off")
            a = nc.NotificationCenterAlerter({})
            with self.assertLogs(a.alerter_logger, level="ERROR") as logs:
                a.send_alert("fail", self.failed_monitor())

        self.assertIn("Couldn't send notification", logs.output[0])

    def test_dry_run_sends_nothing(self, _system):
        with mock.patch.object(nc, "macos", create=True) as macos:
            a = nc.NotificationCenterAlerter({"dry_run": "1"})
            a.send_alert("fail", self.failed_monitor())

        macos.notify.assert_not_called()
