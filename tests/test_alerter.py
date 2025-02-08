# type: ignore
import datetime
import os
import textwrap
import unittest
from unittest import mock

from freezegun import freeze_time

from simplemonitor import util
from simplemonitor.Alerters import alerter, sns
from simplemonitor.Monitors import monitor

# Create a consistent "local" timezone and offset for the tests, for tests that
# compare the offset between UTC and local time. For simplicity and
# predictability, use a time zone that doesn't have daylight savings.
TZ_LOCAL = "MST"
TZ_LOCAL_OFFSET = -7
TZ_UTC = "UTC"


# Default to UTC, then override for tests where we need to have timezone
# specific logic.
@mock.patch.dict(os.environ, {"TZ": TZ_UTC}, clear=True)
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
        with self.assertRaises(ValueError):
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

    @freeze_time("2020-03-10 22:00")  # A Tuesday
    def test_not_allowed_today(self):
        a = alerter.Alerter({"days": "0,2,3,4,5,6"})
        self.assertFalse(a._allowed_today())

    @freeze_time("2020-03-09 20:00")  # Monday UTC, but TZ will push to Tuesday
    def test_not_allowed_today_tz(self):
        """
        Test that we handle timezone conversion properly with disallowed days.
        """
        # Note: This doesn't map with either the regular "local" timezone _or_
        # GMT; that's why we're explicitly setting times_tz offset to a
        # positive value.
        a = alerter.Alerter({"days": "0,2,3,4,5,6", "times_tz": "+05:00"})
        self.assertFalse(a._allowed_today())

    @freeze_time("2020-03-10 22:00")
    def test_allowed_today(self):
        """
        Test that we handle timezone conversion properly with allowed days.
        """
        a = alerter.Alerter({"days": "1"})
        self.assertTrue(a._allowed_today())

    @freeze_time("2020-03-09 20:00")  # Monday UTC, but TZ will push to Tuesday
    def test_allowed_today_tz(self):
        a = alerter.Alerter({"days": "1", "times_tz": "+05:00"})
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
        """
        Test logic with the "only" schedule (only between lower and upper
        bounds).
        """
        a = alerter.Alerter(
            {
                "times_type": "only",
                "time_lower": "10:00",
                "time_upper": "11:00",
            }
        )
        with freeze_time("09:00"):
            self.assertFalse(a._allowed_time())
        with freeze_time("10:30"):
            self.assertTrue(a._allowed_time())
        with freeze_time("12:00"):
            self.assertFalse(a._allowed_time())

    # Influence time_tz indirectly, though we could also set it directly in
    # alerter.Alerter() below.
    @mock.patch.dict(os.environ, {"TZ": TZ_LOCAL}, clear=True)
    def test_allowed_only_tz(self):
        """Test `times_type=only` with the time in local time."""
        a = alerter.Alerter(
            {
                "times_type": "only",
                "time_lower": "09:00",  # 9:00 MST, 16:00 UTC
                "time_upper": "10:00",  # 10:00 MST, 17:00 UTC
            }
        )
        with freeze_time("15:00"):
            self.assertFalse(a._allowed_time())
        with freeze_time("16:30"):
            self.assertTrue(a._allowed_time())
        with freeze_time("18:00"):
            self.assertFalse(a._allowed_time())

    def test_allowed_not(self):
        """Test when using `times_type=not`."""
        a = alerter.Alerter(
            {
                "times_type": "not",
                "time_lower": "10:00",
                "time_upper": "11:00",
            }
        )
        with freeze_time("09:00"):
            self.assertTrue(a._allowed_time())
        with freeze_time("10:30"):
            self.assertFalse(a._allowed_time())
        with freeze_time("12:00"):
            self.assertTrue(a._allowed_time())

    @mock.patch.dict(os.environ, {"TZ": TZ_LOCAL}, clear=True)
    def test_allowed_not_tz(self):
        """Test this variant for a specific timezone."""
        a = alerter.Alerter(
            {
                "times_type": "not",
                "time_lower": "09:00",  # 9:00 MST, 16:00 UTC
                "time_upper": "10:00",  # 10:00 MST, 17:00 UTC
            }
        )
        with freeze_time("15:55"):
            self.assertTrue(a._allowed_time())
        with freeze_time("16:30"):
            self.assertFalse(a._allowed_time())
        with freeze_time("17:00"):
            self.assertTrue(a._allowed_time())

    def test_should_not_alert_ooh(self):
        """Make sure we don't alert outside of hours."""
        config = {
            "times_type": "only",
            "time_lower": "10:00",
            "time_upper": "11:00",
        }
        a = alerter.Alerter(config)
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        with freeze_time("2020-03-10 09:00"):
            # Out of hours on the right day; shouldn't alert
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, ["fail"])

        a = alerter.Alerter(config)
        with freeze_time("2020-03-10 12:00"):
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, ["fail"])

    @freeze_time("2020-03-10 10:30")
    def test_should_alert_ooh(self):
        """Make sure we do alert within scheduled hours."""
        config = {
            "times_type": "only",
            "time_lower": "10:00",
            "time_upper": "11:00",
        }
        a = alerter.Alerter(config)
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)
        self.assertEqual(a._ooh_failures, [])

    @freeze_time("2020-03-10 10:30")
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
        self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
        self.assertEqual(a._ooh_failures, [])

        # It should only alert on the $limit attempt
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)
        self.assertEqual(a._ooh_failures, [])

        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
        self.assertEqual(a._ooh_failures, [])

    @freeze_time("2020-03-10 09:00")
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
        """
        Test that, with `delay` 1 and `support_catchup` = `True`, an alert will
        be sent if a failure from before the period in which notifications are
        allowed, continues once we're within the notification window.
        """
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
        """
        Here, `support_catchup` is unset, so catchup notifications shouldn't be
        sent.
        """
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

    def test_skip_group_alerter(self):
        a = alerter.Alerter({"groups": "test"})
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)

    def test_skip_group_monitor(self):
        a = alerter.Alerter()
        m = monitor.MonitorFail("fail", {"group": "test"})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)

    def test_groups_match(self):
        a = alerter.Alerter({"groups": "test"})
        m = monitor.MonitorFail("fail", {"group": "test"})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)

    def test_groups_multi_match(self):
        a = alerter.Alerter({"groups": "test1, test2"})
        m = monitor.MonitorFail("fail", {"group": "test1"})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)

    def test_groups_all_match(self):
        a = alerter.Alerter({"groups": "_all"})
        m = monitor.MonitorFail("fail", {"group": "test1"})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)

    def test_disabled_monitor_no_alert(self):
        a = alerter.Alerter()
        m = monitor.MonitorFail("fail", {"enabled": 0})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)

    def test_alert_not_urgent(self):
        a = alerter.Alerter()
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)

    def test_no_alert_urgent(self):
        a = alerter.Alerter({"urgent": "1"})
        m = monitor.MonitorFail("fail", {"urgent": "0"})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)

    def test_alert_urgent(self):
        a = alerter.Alerter({"urgent": "1"})
        m = monitor.MonitorFail("fail", {"urgent": "1"})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)

    def test_alert_alerter_not_urgent(self):
        a = alerter.Alerter({"urgent": "0"})
        m = monitor.MonitorFail("fail", {"urgent": "1"})
        m.run_test()
        self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)


class TestMessageBuilding(unittest.TestCase):
    def setUp(self):
        # Because we're instantiating the `alerter.Alerter()` object here, and
        # because the decorator isn't consumed in the setUp routine, need to
        # use `with` here instead for patching the time zone.
        with mock.patch.dict(os.environ, {"TZ": TZ_UTC}, clear=True):
            self.test_alerter = alerter.Alerter()
            self.expected_time_string = "2020-03-10 09:00:00+00:00"

    def test_notification_format_failure(self):
        m = monitor.MonitorFail("test", {})
        m.run_test()
        self.assertEqual(
            self.test_alerter.build_message(
                alerter.AlertLength.NOTIFICATION, alerter.AlertType.FAILURE, m
            ),
            "Monitor test on %s failed" % self.test_alerter.hostname,
        )

    def test_notification_format_success(self):
        m = monitor.MonitorNull("winning", {})
        for _ in range(0, 6):
            m.run_test()
        self.assertEqual(
            self.test_alerter.build_message(
                alerter.AlertLength.NOTIFICATION, alerter.AlertType.SUCCESS, m
            ),
            "Monitor winning on %s succeeded" % self.test_alerter.hostname,
        )

    @freeze_time("2020-03-10 09:00")
    def test_oneline_format_failure(self):
        m = monitor.MonitorFail("test", {})
        m.run_test()
        self.assertEqual(
            self.test_alerter.build_message(
                alerter.AlertLength.ONELINE, alerter.AlertType.FAILURE, m
            ),
            "failure: test on {hostname} failed at {expected_time} (0+00:00:00): This monitor always fails.".format(
                hostname=util.short_hostname(),
                expected_time=self.expected_time_string,
            ),
        )

    def test_oneline_format_success(self):
        m = monitor.MonitorNull("winning", {})
        for _ in range(0, 6):
            m.run_test()
        m.last_result = "a " * 80
        desired = (
            "success: winning on {hostname} succeeded at  (0+00:00:00): ".format(
                hostname=util.short_hostname()
            )
            + "a " * 80
        )
        output = self.test_alerter.build_message(
            alerter.AlertLength.ONELINE, alerter.AlertType.SUCCESS, m
        )
        self.assertEqual(desired, output)

    @freeze_time("2020-03-10 09:00")
    def test_sms_format_failure(self):
        m = monitor.MonitorFail("test", {})
        m.run_test()
        self.assertEqual(
            self.test_alerter.build_message(
                alerter.AlertLength.SMS, alerter.AlertType.FAILURE, m
            ),
            "failure: test on {hostname} failed at {expected_time} (0+00:00:00): This monitor always fails.".format(
                hostname=util.short_hostname(),
                expected_time=self.expected_time_string,
            ),
        )

    def test_sms_format_success(self):
        m = monitor.MonitorNull("winning", {})
        for _ in range(0, 6):
            m.run_test()
        m.last_result = "a " * 80
        self.assertEqual(
            self.test_alerter.build_message(
                alerter.AlertLength.SMS, alerter.AlertType.SUCCESS, m
            ),
            textwrap.shorten(
                "success: winning on {hostname} succeeded at (0+00:00:00): {a}".format(
                    hostname=util.short_hostname(), a=m.last_result
                ),
                width=160,
                placeholder="...",
            ),
        )

    @freeze_time("2020-03-10 09:00")
    def test_full_format_failure(self):
        m = monitor.MonitorFail("test", {})
        m.run_test()
        self.assertEqual(
            self.test_alerter.build_message(
                alerter.AlertLength.FULL, alerter.AlertType.FAILURE, m
            ),
            textwrap.dedent(
                """
                Monitor test on {hostname} failed!
                Failed at: {expected_time} (down 0+00:00:00)
                Virtual failure count: 1
                Additional info: This monitor always fails.
                Description: A monitor which always fails.
                """.format(
                    expected_time=self.expected_time_string,
                    hostname=self.test_alerter.hostname,
                )
            ),
        )

    @freeze_time("2020-03-10 09:00")
    def test_full_format_failure_docs(self):
        m = monitor.MonitorFail("test", {"failure_doc": "whoops"})
        m.run_test()
        self.assertEqual(
            self.test_alerter.build_message(
                alerter.AlertLength.FULL, alerter.AlertType.FAILURE, m
            ),
            textwrap.dedent(
                """
                Monitor test on {host} failed!
                Failed at: {expected_time} (down 0+00:00:00)
                Virtual failure count: 1
                Additional info: This monitor always fails.
                Description: A monitor which always fails.
                Documentation: whoops
                """.format(
                    expected_time=self.expected_time_string,
                    host=self.test_alerter.hostname,
                )
            ),
        )

    @freeze_time("2020-03-10 09:00")
    def test_full_format_success(self):
        m = monitor.MonitorNull("winning", {})
        for _ in range(0, 6):
            m.run_test()
        self.assertEqual(
            self.test_alerter.build_message(
                alerter.AlertLength.FULL, alerter.AlertType.SUCCESS, m
            ),
            textwrap.dedent(
                """
                Monitor winning on {host} succeeded!
                Recovered at: {expected_time} (was down for 0+00:00:00)
                Additional info: 
                Description: (Monitor did not write an auto-biography.)
                """.format(  # noqa: W291
                    expected_time=self.expected_time_string,
                    host=self.test_alerter.hostname,
                )
            ),
        )

    def test_was_downtime(self):
        m = monitor.MonitorFail("test", {})
        with freeze_time("2020-03-10 09:00") as frozen_time:
            for _ in range(0, 6):
                m.run_test()
                frozen_time.tick(30)
            self.assertEqual(m.get_wasdowntime(), util.UpDownTime(0, 0, 2, 30))


class TestMessageBuildingTZ(TestMessageBuilding):
    def setUp(self):
        super().setUp()
        self.test_alerter._tz = "Europe/Warsaw"
        self.expected_time_string = "2020-03-10 10:00:00+01:00"


class TestSNSAlerter(unittest.TestCase):
    def test_config(self):
        with self.assertRaises(util.AlerterConfigurationError):
            sns.SNSAlerter({})
        with self.assertRaises(util.AlerterConfigurationError):
            sns.SNSAlerter({"topic": "a", "number": "b"})

    def test_urgent(self):
        a = sns.SNSAlerter({"topic": "a"})
        self.assertEqual(a.urgent, True)

    def test_not_urgent(self):
        a = sns.SNSAlerter({"topic": "a", "urgent": 0})
        self.assertEqual(a.urgent, False)


@mock.patch.dict(os.environ, {"TZ": TZ_LOCAL}, clear=True)
class TestDescription(unittest.TestCase):
    def test_times_always(self):
        a = alerter.Alerter({"times_type": "always"})
        self.assertEqual(a._describe_times(), "(always)")

    def test_times_only_times(self):
        a = alerter.Alerter(
            {"times_type": "only", "time_lower": "09:00", "time_upper": "10:00"}
        )
        self.assertEqual(
            a._describe_times(), f"only between 09:00 and 10:00 ({TZ_LOCAL}) on any day"
        )

    def test_times_only_days(self):
        a = alerter.Alerter(
            {
                "times_type": "only",
                "time_lower": "09:00",
                "time_upper": "10:00",
                "days": "0,1,2",
            }
        )
        self.assertEqual(
            a._describe_times(),
            f"only between 09:00 and 10:00 ({TZ_LOCAL}) on Mon, Tue, Wed",
        )

    def test_times_not_time(self):
        a = alerter.Alerter(
            {"times_type": "not", "time_lower": "09:00", "time_upper": "10:00"}
        )
        self.assertEqual(
            a._describe_times(),
            f"any time except between 09:00 and 10:00 ({TZ_LOCAL}) on any day",
        )

    def test_times_not_days(self):
        a = alerter.Alerter(
            {
                "times_type": "not",
                "time_lower": "09:00",
                "time_upper": "10:00",
                "days": "3,4,5,6",
            }
        )
        self.assertEqual(
            a._describe_times(),
            f"any time except between 09:00 and 10:00 ({TZ_LOCAL}) on Thu, Fri, Sat, Sun",
        )
