# type: ignore
import configparser
import os
import os.path
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from simplemonitor import Alerters, monitor, simplemonitor
from simplemonitor.Loggers import network
from simplemonitor.Monitors.monitor import MonitorFail, MonitorNull


class TestMonitor(unittest.TestCase):
    def test_MonitorConfigInterval(self):
        with self.assertRaises(configparser.NoOptionError):
            testargs = ["monitor.py", "-f", "tests/monitor-nointerval.ini"]
            with patch.object(sys, "argv", testargs):
                monitor.main()
        with self.assertRaises(ValueError):
            testargs = ["monitor.py", "-f", "tests/monitor-badinterval.ini"]
            with patch.object(sys, "argv", testargs):
                monitor.main()

    def test_file_hup(self):
        temp_file_info = tempfile.mkstemp()
        os.close(temp_file_info[0])
        temp_file_name = temp_file_info[1]
        s = simplemonitor.SimpleMonitor(
            Path("tests/monitor-empty.ini"), hup_file=temp_file_name
        )
        s._check_hup_file()
        time.sleep(2)
        Path(temp_file_name).touch()
        self.assertEqual(
            s._check_hup_file(),
            True,
            "check_hup_file did not trigger",
        )
        self.assertEqual(
            s._check_hup_file(),
            False,
            "check_hup_file should not have triggered",
        )
        os.unlink(temp_file_name)

    def test_disabled_monitor_not_run(self):
        s = simplemonitor.SimpleMonitor(Path("tests/monitor-empty.ini"))
        m = MonitorNull("unnamed", {"enabled": 0})
        with patch.object(m, "run_test") as mock_method:
            s.add_monitor("test", m)
            s.run_tests()
        mock_method.assert_not_called()

    def test_enabled_monitor_run(self):
        s = simplemonitor.SimpleMonitor(Path("tests/monitor-empty.ini"))
        m = MonitorNull("unnamed", {"enabled": 1})
        with patch.object(m, "run_test") as mock_method:
            s.add_monitor("test", m)
            s.run_tests()
        mock_method.assert_called_once()


class TestPidFile(unittest.TestCase):
    def test_pidfile(self):
        s = simplemonitor.SimpleMonitor("tests/monitor-empty.ini")
        s.pidfile = "__pid_test"
        try:
            os.unlink(s.pidfile)
        except IOError:
            pass
        s._create_pid_file()
        self.assertTrue(os.path.exists(s.pidfile))
        s._remove_pid_file()
        self.assertFalse(os.path.exists(s.pidfile))


class TestSanity(unittest.TestCase):
    def test_config_has_alerting(self):
        m = simplemonitor.SimpleMonitor("tests/monitor-empty.ini")
        self.assertFalse(m.verify_alerting())

        m.add_alerter("testing", Alerters.alerter.Alerter({}))
        self.assertTrue(m.verify_alerting())

        m = simplemonitor.SimpleMonitor("tests/monitor-empty.ini")
        m.add_logger(
            "testing",
            network.NetworkLogger({"host": "localhost", "port": 1234, "key": "hello"}),
        )
        self.assertTrue(m.verify_alerting())


class TestNetworkMonitors(unittest.TestCase):
    def test_simple(self):
        s = simplemonitor.SimpleMonitor("tests/monitor-empty.ini")
        m = MonitorNull()
        data = {
            "test1": {"cls_type": m.monitor_type, "data": m.to_python_dict()},
            "test2": {"cls_type": m.monitor_type, "data": m.to_python_dict()},
        }
        s.update_remote_monitor(data, "remote.host")
        self.assertIn("remote.host", s.remote_monitors)
        self.assertIn("test1", s.remote_monitors["remote.host"])
        self.assertIn("test2", s.remote_monitors["remote.host"])

    def test_removal(self):
        s = simplemonitor.SimpleMonitor("tests/monitor-empty.ini")
        m = MonitorNull()
        data = {
            "test1": {"cls_type": m.monitor_type, "data": m.to_python_dict()},
            "test2": {"cls_type": m.monitor_type, "data": m.to_python_dict()},
        }
        s.update_remote_monitor(data, "remote.host")
        data = {
            "test1": {"cls_type": m.monitor_type, "data": m.to_python_dict()},
        }
        s.update_remote_monitor(data, "remote.host")
        self.assertIn("test1", s.remote_monitors["remote.host"])
        self.assertNotIn("test2", s.remote_monitors["remote.host"])


class TestFailedLogic(unittest.TestCase):
    def test_disabled(self):
        s = simplemonitor.SimpleMonitor("tests/monitor-empty.ini")
        m1 = MonitorFail("fail", config_options={})
        m2 = MonitorNull("null", config_options={"enabled": "0"})
        s.add_monitor("fail", m1)
        s.add_monitor("null", m2)
        m2.reset_dependencies()
        m1.run_test()
        failed = s._failed_monitors()
        self.assertListEqual(["fail", "null"], failed)

    def test_no_disabled(self):
        s = simplemonitor.SimpleMonitor("tests/monitor-empty.ini")
        m1 = MonitorFail("fail", config_options={})
        m2 = MonitorNull("null", config_options={})
        s.add_monitor("fail", m1)
        s.add_monitor("null", m2)
        m2.reset_dependencies()
        m1.run_test()
        failed = s._failed_monitors()
        self.assertListEqual(["fail"], failed)

    def test_no_failed(self):
        s = simplemonitor.SimpleMonitor("tests/monitor-empty.ini")
        m1 = MonitorNull("null1", config_options={})
        m2 = MonitorNull("null2", config_options={})
        s.add_monitor("null1", m1)
        s.add_monitor("null2", m2)
        m2.reset_dependencies()
        m1.run_test()
        failed = s._failed_monitors()
        self.assertListEqual([], failed)
