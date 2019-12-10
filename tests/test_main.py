import sys
import unittest
import tempfile
import pathlib
import os
import os.path
import time

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
