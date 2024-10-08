# type: ignore
import datetime
import os
import textwrap
import unittest

import arrow
import pytest
from freezegun import freeze_time

from simplemonitor import util
from simplemonitor.Alerters import alerter, sns
from simplemonitor.Monitors import monitor


class TestAlerter(unittest.TestCase):
    def setUp(self):
        # Work around to fix the freezegun times later to our local TZ, else they're UTC
        # and the time compared to is local (as it should be)
        self.tz = os.environ.get("TZ", "local")
        a = arrow.now()
        self.utcoffset = a.utcoffset()

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

    def test_not_allowed_today(self):
        # a Tuesday
        with freeze_time("2020-03-10", tz_offset=self.utcoffset):
            a = alerter.Alerter({"days": "0,2,3,4,5,6"})
            self.assertFalse(a._allowed_today())

    @freeze_time(
        "2020-03-09 22:00:00+00:00"
    )  # a Monday, but the TZ will push to Tuesday
    def test_not_allowed_today_tz(self):
        a = alerter.Alerter({"days": "0,2,3,4,5,6", "times_tz": "+05:00"})
        self.assertFalse(a._allowed_today())

    def test_allowed_today(self):
        with freeze_time("2020-03-10", tz_offset=self.utcoffset):
            a = alerter.Alerter({"days": "1"})
            self.assertTrue(a._allowed_today())

    @freeze_time(
        "2020-03-09 22:00:00+00:00"
    )  # a Monday, but the TZ will push to Tuesday
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
        a = alerter.Alerter(
            {
                "times_type": "only",
                "time_lower": "10:00",
                "time_upper": "11:00",
                "times_tz": "local",
            }
        )
        with freeze_time("09:00", tz_offset=-self.utcoffset):
            self.assertFalse(a._allowed_time())
        with freeze_time("10:30", tz_offset=-self.utcoffset):
            self.assertTrue(a._allowed_time())
        with freeze_time("12:00", tz_offset=-self.utcoffset):
            self.assertFalse(a._allowed_time())

    def test_allowed_only_tz(self):
        a = alerter.Alerter(
            {
                "times_type": "only",
                "time_lower": "15:00",
                "time_upper": "16:00",
                "times_tz": "+05:00",
            }
        )
        with freeze_time("09:00"):
            self.assertFalse(a._allowed_time())
        with freeze_time("10:30"):
            self.assertTrue(a._allowed_time())
        with freeze_time("12:00"):
            self.assertFalse(a._allowed_time())

    def test_allowed_not(self):
        a = alerter.Alerter(
            {
                "times_type": "not",
                "time_lower": "10:00",
                "time_upper": "11:00",
                "times_tz": "local",
            }
        )
        with freeze_time("09:00", tz_offset=-self.utcoffset):
            self.assertTrue(a._allowed_time())
        with freeze_time("10:30", tz_offset=-self.utcoffset):
            print(arrow.get())
            self.assertFalse(a._allowed_time())
        with freeze_time("12:00", tz_offset=-self.utcoffset):
            self.assertTrue(a._allowed_time())

    def test_allowed_not_tz(self):
        a = alerter.Alerter(
            {
                "times_type": "not",
                "time_lower": "15:00",
                "time_upper": "16:00",
                "times_tz": "+05:00",
            }
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

    @pytest.mark.skip("TZ test logic need fixing")
    def test_should_alert_ooh(self):
        config = {"times_type": "only", "time_lower": "10:00", "time_upper": "11:00"}
        a = alerter.Alerter(config)
        m = monitor.MonitorFail("fail", {})
        m.run_test()
        with freeze_time("2020-03-10 10:30", tz_offset=self.utcoffset):
            self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)
            self.assertEqual(a._ooh_failures, [])

    @pytest.mark.skip("TZ test logic need fixing")
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
        with freeze_time("2020-03-10 10:30", tz_offset=self.utcoffset):
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, [])

            m.run_test()
            self.assertEqual(a.should_alert(m), alerter.AlertType.FAILURE)
            self.assertEqual(a._ooh_failures, [])

            m.run_test()
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, [])

    @pytest.mark.skip("TZ test logic need fixing")
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
        with freeze_time("2020-03-10 09:00", tz_offset=self.utcoffset):
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

    @pytest.mark.skip("TZ test logic need fixing")
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
        with freeze_time("2020-03-10 09:00", tz_offset=self.utcoffset):
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, ["fail"])

        with freeze_time("2020-03-10 10:30", tz_offset=self.utcoffset):
            self.assertEqual(a.should_alert(m), alerter.AlertType.CATCHUP)
            self.assertEqual(a._ooh_failures, [])

    @pytest.mark.skip("TZ test logic need fixing")
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
        with freeze_time("2020-03-10 09:00", tz_offset=self.utcoffset):
            self.assertEqual(a.should_alert(m), alerter.AlertType.NONE)
            self.assertEqual(a._ooh_failures, ["fail"])

        with freeze_time("2020-03-10 10:30", tz_offset=self.utcoffset):
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
        self.test_alerter = alerter.Alerter()
        self.freeze_time_value = "2020-03-10 09:00"
        self.tz = os.environ.get("TZ", "local")
        self.expected_time_string = (
            arrow.get("2020-03-10 09:00:00+00:00").to(self.tz).format()
        )
        a = arrow.now()
        self.utcoffset = a.utcoffset()

    def test_notification_format_failure(self):
        m = monitor.MonitorFail("test", {})
        with freeze_time(self.freeze_time_value):
            m.run_test()
            self.assertEqual(
                self.test_alerter.build_message(
                    alerter.AlertLength.NOTIFICATION, alerter.AlertType.FAILURE, m
                ),
                "Monitor test on %s failed" % self.test_alerter.hostname,
            )

    def test_notification_format_success(self):
        m = monitor.MonitorNull("winning", {})
        with freeze_time(self.freeze_time_value):
            for _ in range(0, 6):
                m.run_test()
            self.assertEqual(
                self.test_alerter.build_message(
                    alerter.AlertLength.NOTIFICATION, alerter.AlertType.SUCCESS, m
                ),
                "Monitor winning on %s succeeded" % self.test_alerter.hostname,
            )

    def test_oneline_format_failure(self):
        m = monitor.MonitorFail("test", {})
        with freeze_time(self.freeze_time_value):
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
        with freeze_time(self.freeze_time_value):
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

    def test_sms_format_failure(self):
        m = monitor.MonitorFail("test", {})
        with freeze_time(self.freeze_time_value):
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
        with freeze_time(self.freeze_time_value):
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

    def test_full_format_failure(self):
        m = monitor.MonitorFail("test", {})
        with freeze_time(self.freeze_time_value):
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

    def test_full_format_failure_docs(self):
        m = monitor.MonitorFail("test", {"failure_doc": "whoops"})
        with freeze_time(self.freeze_time_value):
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

    def test_full_format_success(self):
        m = monitor.MonitorNull("winning", {})
        with freeze_time(self.freeze_time_value):
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
        with freeze_time(self.freeze_time_value) as frozen_time:
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


class TestDescription(unittest.TestCase):
    def setUp(self) -> None:
        self.tz = os.environ.get("TZ", "local")

    def test_times_always(self):
        a = alerter.Alerter({"times_type": "always"})
        self.assertEqual(a._describe_times(), "(always)")

    def test_times_only_times(self):
        a = alerter.Alerter(
            {"times_type": "only", "time_lower": "09:00", "time_upper": "10:00"}
        )
        self.assertEqual(
            a._describe_times(), f"only between 09:00 and 10:00 ({self.tz}) on any day"
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
            f"only between 09:00 and 10:00 ({self.tz}) on Mon, Tue, Wed",
        )

    def test_times_not_time(self):
        a = alerter.Alerter(
            {"times_type": "not", "time_lower": "09:00", "time_upper": "10:00"}
        )
        self.assertEqual(
            a._describe_times(),
            f"any time except between 09:00 and 10:00 ({self.tz}) on any day",
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
            f"any time except between 09:00 and 10:00 ({self.tz}) on Thu, Fri, Sat, Sun",
        )
