import sys
import unittest

try:
    # python 3.4+ should use builtin unittest.mock not mock package
    from unittest.mock import patch
except ImportError:
    from mock import patch

import monitor
import util

if sys.version_info[0] == 2:
    import ConfigParser as configparser
else:
    import configparser

class TestMonitor(unittest.TestCase):

    def test_MonitorConfigInterval(self):
        with self.assertRaises(SystemExit):
            testargs = ["monitor.py", "-f", "tests/mocks/ini/monitor-nointerval.ini"]
            with patch.object(sys, 'argv', testargs):
                monitor.main()
        with self.assertRaises(SystemExit):
            testargs = ["monitor.py", "-f", "tests/mocks/ini/monitor-badinterval.ini"]
            with patch.object(sys, 'argv', testargs):
                monitor.main()
