# type: ignore
import os
import os.path
import pathlib
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from simplemonitor import Alerters, monitor, simplemonitor
from simplemonitor.Loggers import network
from simplemonitor.Monitors.monitor import MonitorNull


class TestMonitor(unittest.TestCase):
    def test_MonitorConfigInterval(self):
        with self.assertRaises(SystemExit):
            testargs = ["monitor.py", "-f", "tests/mocks/ini/monitor-nointerval.ini"]
            with patch.object(sys, "argv", testargs):
                monitor.main()
        with self.assertRaises(SystemExit):
            testargs = ["monitor.py", "-f", "tests/mocks/ini/monitor-badinterval.ini"]
            with patch.object(sys, "argv", testargs):
                monitor.main()

    def test_file_hup(self):
        temp_file_info = tempfile.mkstemp()
        os.close(temp_file_info[0])
        temp_file_name = temp_file_info[1]
        monitor.check_hup_file(temp_file_name)
        time.sleep(2)
        pathlib.Path(temp_file_name).touch()
        self.assertEqual(
            monitor.check_hup_file(temp_file_name),
            True,
            "check_hup_file did not trigger",
        )
        self.assertEqual(
            monitor.check_hup_file(temp_file_name),
            False,
            "check_hup_file should not have triggered",
        )
        os.unlink(temp_file_name)


class TestSanity(unittest.TestCase):
    def test_config_has_alerting(self):
        m = simplemonitor.SimpleMonitor()
        self.assertFalse(m.verify_alerting())

        m.add_alerter("testing", Alerters.alerter.Alerter({}))
        self.assertTrue(m.verify_alerting())

        m = simplemonitor.SimpleMonitor()
        m.add_logger(
            "testing",
            network.NetworkLogger({"host": "localhost", "port": 1234, "key": "hello"}),
        )
        self.assertTrue(m.verify_alerting())


class TestNetworkMonitors(unittest.TestCase):
    def test_simple(self):
        s = simplemonitor.SimpleMonitor()
        m = MonitorNull()
        data = {
            "test1": {"cls_type": m._type, "data": m.to_python_dict()},
            "test2": {"cls_type": m._type, "data": m.to_python_dict()},
        }
        s.update_remote_monitor(data, "remote.host")
        self.assertIn("remote.host", s.remote_monitors)
        self.assertIn("test1", s.remote_monitors["remote.host"])
        self.assertIn("test2", s.remote_monitors["remote.host"])

    def test_removal(self):
        s = simplemonitor.SimpleMonitor()
        m = MonitorNull()
        data = {
            "test1": {"cls_type": m._type, "data": m.to_python_dict()},
            "test2": {"cls_type": m._type, "data": m.to_python_dict()},
        }
        s.update_remote_monitor(data, "remote.host")
        data = {
            "test1": {"cls_type": m._type, "data": m.to_python_dict()},
        }
        s.update_remote_monitor(data, "remote.host")
        self.assertIn("test1", s.remote_monitors["remote.host"])
        self.assertNotIn("test2", s.remote_monitors["remote.host"])
