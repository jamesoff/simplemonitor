import sys
import unittest

from unittest.mock import patch

import monitor


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
