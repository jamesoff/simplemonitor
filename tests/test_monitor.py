import unittest
import datetime
import monitor
import Monitors.monitor
from simplemonitor import SimpleMonitor


class TestMonitor(unittest.TestCase):

    safe_config = {"partition": "/", "limit": "10G"}

    one_KB = 1024
    one_MB = one_KB * 1024
    one_GB = one_MB * 1024
    one_TB = one_GB * 1024

    def test_MonitorInit(self):
        m = Monitors.monitor.Monitor(
            config_options={
                "depend": "a, b",
                "urgent": 0,
                "tolerance": 2,
                "remote_alert": 1,
                "recover_command": "true",
            }
        )
        self.assertEqual(m.name, "unnamed", "Monitor did not set name")
        self.assertEqual(m.urgent, 0, "Monitor did not set urgent")
        self.assertEqual(m._tolerance, 2, "Monitor did not set tolerance")
        self.assertTrue(m.remote_alerting, "Monitor did not set remote_alerting")
        self.assertEqual(
            m._recover_command, "true", "Monitor did not set recover_command"
        )
        with self.assertRaises(ValueError):
            m.minimum_gap = -1
        with self.assertRaises(TypeError):
            m.minimum_gap = "zero"
        with self.assertRaises(TypeError):
            m.notify = "true"
        m.notify = False
        self.assertEqual(m.notify, False, "monitor did not unset notify")
        m.notify = True
        self.assertEqual(m.notify, True, "monitor did not set notify")
        with self.assertRaises(TypeError):
            m.urgent = "true"
        m.urgent = True
        self.assertEqual(m.urgent, True, "monitor did not set urgent")
        m.urgent = 0
        self.assertEqual(m.urgent, False, "monitor did not unset urgent with an int")
        m.urgent = 1
        self.assertEqual(m.urgent, True, "monitor did not set urgent with an int")
        with self.assertRaises(TypeError):
            m.dependencies = "no at a list"
        m.dependencies = ["a", "b"]
        self.assertEqual(
            m.dependencies,
            ["a", "b"],
            "monitor did not set or return dependencies correctly",
        )
        self.assertEqual(
            m.remaining_dependencies,
            ["a", "b"],
            "monitor did not set remaining dependencies",
        )
        m.dependency_succeeded("a")
        self.assertEqual(
            m.remaining_dependencies,
            ["b"],
            "monitor did not remove dependencies from list",
        )
        m.dependency_succeeded("a")  # should be safe to remove again

    def test_MonitorSuccess(self):
        m = Monitors.monitor.Monitor()
        m.record_success("yay")
        self.assertEqual(m.get_error_count(), 0, "Error count is not 0")
        self.assertEqual(m.get_success_count(), 1, "Success count is not 1")
        self.assertEqual(m.tests_run, 1, "Tests run is not 1")
        self.assertFalse(m.was_skipped, "was_skipped is not false")
        self.assertEqual(m.last_result, "yay", "Last result is not correct")
        self.assertEqual(m.state(), True, "monitor did not report state correctly")
        self.assertEqual(m.virtual_fail_count(), 0, "monitor did not report VFC of 0")
        self.assertEqual(m.test_success(), True, "test_success is not True")

    def test_MonitorFail(self):
        m = Monitors.monitor.Monitor()
        m.record_fail("boo")
        self.assertEqual(m.get_error_count(), 1, "Error count is not 1")
        self.assertEqual(m.get_success_count(), 0, "Success count is not 0")
        self.assertEqual(m.tests_run, 1, "Tests run is not 1")
        self.assertFalse(m.was_skipped, "was_skipped is not false")
        self.assertEqual(m.last_result, "boo", "Last result is not correct")
        self.assertEqual(m.state(), False, "monitor did not report state correctly")
        self.assertEqual(
            m.virtual_fail_count(), 1, "monitor did not calculate VFC correctly"
        )
        self.assertEqual(m.test_success(), False, "test_success is not False")
        self.assertEqual(m.first_failure(), True, "First failure is not False")

        m.record_fail("cows")
        self.assertEqual(m.get_error_count(), 2, "Error count is not 2")
        self.assertEqual(m.first_failure(), False, "first_failure is not False")
        self.assertEqual(m.state(), False, "state is not False")

    def test_MonitorWindows(self):
        m = Monitors.monitor.Monitor()
        self.assertFalse(m.is_windows())

    def test_MonitorSkip(self):
        m = Monitors.monitor.Monitor()
        m.record_skip("a")
        self.assertEqual(m.get_success_count(), 1, "Success count is not 1")
        self.assertTrue(m.was_skipped, "was_skipped is not true")
        self.assertEqual(m.skip_dep, "a", "skip_dep is not correct")
        self.assertTrue(m.skipped(), "skipped() is not true")

    def test_MonitorConfig(self):
        config_options = {
            "test_string": "a string",
            "test_int": "3",
            "test_[int]": "1,2, 3",
            "test_[str]": "a, b,c",
            "test_bool1": "1",
            "test_bool2": "yes",
            "test_bool3": "true",
            "test_bool4": "0",
        }
        self.assertEqual(
            Monitors.monitor.Monitor.get_config_option(config_options, "test_string"),
            "a string",
        )
        self.assertEqual(
            Monitors.monitor.Monitor.get_config_option(
                config_options, "test_int", required_type="int"
            ),
            3,
        )
        self.assertEqual(
            Monitors.monitor.Monitor.get_config_option(
                config_options, "test_[int]", required_type="[int]"
            ),
            [1, 2, 3],
        )
        self.assertEqual(
            Monitors.monitor.Monitor.get_config_option(
                config_options, "test_[str]", required_type="[str]"
            ),
            ["a", "b", "c"],
        )
        for bool_test in list(range(1, 4)):
            self.assertEqual(
                Monitors.monitor.Monitor.get_config_option(
                    config_options,
                    "test_bool{0}".format(bool_test),
                    required_type="bool",
                ),
                True,
            )
        self.assertEqual(
            Monitors.monitor.Monitor.get_config_option(
                config_options, "test_bool4", required_type="bool"
            ),
            False,
        )

    def test_downtime(self):
        m = Monitors.monitor.Monitor()
        m.failed_at = datetime.datetime.utcnow()
        self.assertEqual(m.get_downtime(), (0, 0, 0, 0))

        m.failed_at = None
        self.assertEqual(m.get_downtime(), (0, 0, 0, 0))

        now = datetime.datetime.utcnow()
        two_h_thirty_m_ago = now - datetime.timedelta(hours=2, minutes=30)
        yesterday = now - datetime.timedelta(days=1)

        m.failed_at = two_h_thirty_m_ago
        self.assertEqual(m.get_downtime(), (0, 2, 30, 0))

        m.failed_at = yesterday
        self.assertEqual(m.get_downtime(), (1, 0, 0, 0))

    def test_sighup(self):
        monitor.setup_signals()

        self.assertEqual(monitor.need_hup, False, "need_hup did not start False")
        monitor.handle_sighup(None, None)
        self.assertEqual(monitor.need_hup, True, "need_hup did not get set to True")

        m = SimpleMonitor()
        m = monitor.load_monitors(m, "tests/monitors-prehup.ini")
        self.assertEqual(
            m.monitors["monitor1"].type, "null", "monitor1 did not load correctly"
        )
        self.assertEqual(
            m.monitors["monitor2"].type, "host", "monitor2 did not load correctly"
        )
        self.assertEqual(
            m.monitors["monitor2"].host, "127.0.0.1", "monitor2 did not load correctly"
        )

        m = monitor.load_monitors(m, "tests/monitors-posthup.ini")
        self.assertEqual(m.monitors["monitor1"].type, "null", "monitor1 changed type")
        self.assertEqual(m.monitors["monitor2"].type, "host", "monitor2 changed type")
        self.assertEqual(
            m.monitors["monitor2"].host, "127.0.0.2", "monitor2 did not update config"
        )
