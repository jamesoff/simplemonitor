# type: ignore
import datetime
import unittest

from freezegun import freeze_time

from simplemonitor import util
from simplemonitor.Alerters import alerter, sns
from simplemonitor.Monitors import monitor


class TestAlerter(unittest.TestCase):
    def test_groups(self):
        config_options = {"groups": "a,b,c"}
        a = alerter.Alerter(config_options)
        self.assertEqual(["a", "b", "c"], a.groups)

    def test_times_always(self):
        config_options = {"times_type": "always"}
        a = alerter.Alerter(config_options)
        self.assertEqual(a._times_type, alerter.AlertTimeFilter.ALWAYS)
        self.assertEqual(a._time_info, (None, None))

    def test_times_only(self):
        config_options = {
            "times_type": "only",
            "time_lower": "10:00",
            "time_upper": "11:00",
        }
        a = alerter.Alerter(config_options)
        self.assertEqual(a._times_type, alerter.AlertTimeFilter.ONLY)
        self.assertEqual(a._time_info, (datetime.time(10, 00), datetime.time(11, 00)))

    def test_times_not(self):
        config_options = {
            "times_type": "not",
            "time_lower": "10:00",
            "time_upper": "11:00",
        }
        a = alerter.Alerter(config_options)
        self.assertEqual(a._times_type, alerter.AlertTimeFilter.NOT)
        self.assertEqual(a._time_info, (datetime.time(10, 00), datetime.time(11, 00)))

    def test_times_broken(self):
        config_options = {
            "times_type": "fake",
            "time_lower": "10:00",
            "time_upper": "11:00",
        }
        with self.assertRaises(util.AlerterConfigurationError):
            alerter.Alerter(config_options)

    def test_days(self):
        config_options = {"days": "0,1,4"}
        a = alerter.Alerter(config_options)
        self.assertEqual(a._days, [0, 1, 4])

    def test_delay(self):
        config_options = {"delay": "1"}
        a = alerter.Alerter(config_options)
        self.assertEqual(a._delay_notification, True)

    def test_dryrun(self):
        config_options = {"dry_run": "1"}
        a = alerter.Alerter(config_options)
        self.assertEqual(a._dry_run, True)

    def test_oohrecovery(self):
        config_otions = {"ooh_recovery": "1"}
        a = alerter.Alerter(config_otions)
        self.assertEqual(a._ooh_recovery, True)

    def test_dependencies(self):
        config_options = {"depend": "a,b,c"}
        a = alerter.Alerter(config_options)
        self.assertEqual(
            a.dependencies, ["a", "b", "c"], "Alerter did not store dependencies"
        )
        self.assertEqual(
            a.check_dependencies(["d", "e"]), True, "Alerter thinks a dependency failed"
        )
        self.assertEqual(
            a.check_dependencies(["a"]),
            False,
            "Alerter did not notice a dependency failed",
        )

    def test_limit(self):
        config_options = {"limit": "5"}
        a = alerter.Alerter(config_options)
        self.assertEqual(a._limit, 5)

    def test_repeat(self):
        config_options = {"repeat": "5"}
        a = alerter.Alerter(config_options)
        self.assertEqual(a._repeat, 5)

    def test_should_alert_unavailable(self):
        a = alerter.Alerter(None)
        a.available = False
        m = monitor.MonitorNull()
        self.assertEqual(
            a.should_alert(m),
            alerter.AlertType.NONE,
            "Alerter did not handle being unavailable",
        )

    def test_should_alert_basic_failure(self):
        # no special alert config
        a = alerter.Alerter(None)
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)

    def test_should_alert_only_failure(self):
        # no special alert config
        a = alerter.Alerter({"only_failures": True})
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)

    def test_should_alert_basic_none(self):
        a = alerter.Alerter(None)
        m = monitor.MonitorNull()
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)

    def test_should_alert_basic_success(self):
        a = alerter.Alerter(None)
        m = monitor.MonitorFail("fail", {})
        for _ in range(0, 6):
            m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.SUCCESS)

    def test_should_not_alert_basic_success(self):
        a = alerter.Alerter({"only_failures": True})
        m = monitor.MonitorFail("fail", {})
        for _ in range(0, 6):
            m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)

    @freeze_time("2020-03-10")  # a Tuesday
    def test_not_allowed_today(self):
        a = alerter.Alerter({"days": "0,2,3,4,5,6"})
        self.assertFalse(a._allowed_today())

    @freeze_time("2020-03-10")
    def test_allowed_today(self):
        a = alerter.Alerter({"days": "1"})
        self.assertTrue(a._allowed_today())

    @freeze_time("2020-03-10")
    def test_allowed_default(self):
        a = alerter.Alerter({})
        self.assertTrue(a._allowed_today())

    @freeze_time("10:00")
    def test_allowed_always(self):
        a = alerter.Alerter({})
        self.assertTrue(a._allowed_time())

    def test_allowed_only(self):
        a = alerter.Alerter(
            {"times_type": "only", "time_lower": "10:00", "time_upper": "11:00"}
        )
        with freeze_time("09:00"):
            self.assertFalse(a._allowed_time())
        with freeze_time("10:30"):
            self.assertTrue(a._allowed_time())
        with freeze_time("12:00"):
            self.assertFalse(a._allowed_time())

    def test_allowed_not(self):
        a = alerter.Alerter(
            {"times_type": "not", "time_lower": "10:00", "time_upper": "11:00"}
        )
        with freeze_time("09:00"):
            self.assertTrue(a._allowed_time())
        with freeze_time("10:30"):
            self.assertFalse(a._allowed_time())
        with freeze_time("12:00"):
            self.assertTrue(a._allowed_time())

    def test_should_not_alert_ooh(self):
        config = {"times_type": "only", "time_lower": "10:00", "time_upper": "11:00"}
        a = alerter.Alerter(config)
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        with freeze_time("2020-03-10 09:00"):
            # out of hours on the right day; shouldn't alert
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, ["fail"])
        a = alerter.Alerter(config)
        with freeze_time("2020-03-10 12:00"):
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, ["fail"])

    def test_should_alert_ooh(self):
        config = {"times_type": "only", "time_lower": "10:00", "time_upper": "11:00"}
        a = alerter.Alerter(config)
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        with freeze_time("2020-03-10 10:30"):
            self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)
            self.assertEqual(a._ooh_failures, [])

    def test_should_alert_limit(self):
        config = {
            "times_type": "only",
            "time_lower": "10:00",
            "time_upper": "11:00",
            "limit": 2,
        }
        a = alerter.Alerter(config)
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        with freeze_time("2020-03-10 10:30"):
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, [])

            m.run_test()
            self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)
            self.assertEqual(a._ooh_failures, [])

            m.run_test()
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, [])

    def test_should_alert_limit_ooh(self):
        config = {
            "times_type": "only",
            "time_lower": "10:00",
            "time_upper": "11:00",
            "limit": 2,
        }
        a = alerter.Alerter(config)
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        with freeze_time("2020-03-10 09:00"):
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, [])

            a = alerter.Alerter(config)
            m.run_test()
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, ["fail"])

            a = alerter.Alerter(config)
            m.run_test()
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, [])

    def test_should_alert_catchup(self):
        config = {
            "delay": 1,
            "times_type": "only",
            "time_lower": "10:00",
            "time_upper": "11:00",
        }
        a = alerter.Alerter(config)
        a.support_catchup = True
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        with freeze_time("2020-03-10 09:00"):
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, ["fail"])

        with freeze_time("2020-03-10 10:30"):
            self.assertEqual(a.should_alert(m), alerter.AlertType.CATCHUP)
            self.assertEqual(a._ooh_failures, [])

    def test_should_alert_no_catchup(self):
        config = {
            "delay": 1,
            "times_type": "only",
            "time_lower": "10:00",
            "time_upper": "11:00",
        }
        a = alerter.Alerter(config)
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        with freeze_time("2020-03-10 09:00"):
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, ["fail"])

        with freeze_time("2020-03-10 10:30"):
            self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)
            self.assertEqual(a._ooh_failures, [])


class TestSNSAlerter(unittest.TestCase):
    def test_config(self):
        with self.assertRaises(util.AlerterConfigurationError):
            sns.SNSAlerter({})
        with self.assertRaises(util.AlerterConfigurationError):
            sns.SNSAlerter({"topic": "a", "number": "b"})
