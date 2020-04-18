# type: ignore
import os.path
import tempfile
import time
import unittest
from unittest.mock import patch

from freezegun import freeze_time

from simplemonitor.Loggers import logger
from simplemonitor.Loggers.file import FileLogger
from simplemonitor.Monitors.monitor import MonitorNull
from simplemonitor.simplemonitor import SimpleMonitor


class TestLogger(unittest.TestCase):
    def test_default(self):
        config_options = {}
        test_logger = logger.Logger(config_options)
        self.assertEqual(
            test_logger.dependencies, [], "logger did not set default dependencies"
        )

    def test_dependencies(self):
        config_options = {"depend": ["a", "b"]}
        test_logger = logger.Logger(config_options)
        self.assertEqual(
            test_logger.dependencies,
            ["a", "b"],
            "logger did not set dependencies to given list",
        )
        with self.assertRaises(TypeError):
            test_logger.dependencies = "moo"
        test_logger.dependencies = ["b", "c"]
        self.assertEqual(
            test_logger.check_dependencies(["a"]),
            True,
            "logger thought a dependency had failed",
        )
        self.assertEqual(
            test_logger.connected, True, "logger did not think it was connected"
        )
        self.assertEqual(
            test_logger.check_dependencies(["a", "b"]),
            False,
            "logger did not think a dependency failed",
        )
        self.assertEqual(
            test_logger.connected, False, "logger thought it was connected"
        )

    def test_groups(self):
        with patch.object(logger.Logger, "save_result2") as mock_method:
            this_logger = logger.Logger({"groups": "nondefault"})
            s = SimpleMonitor()
            s.add_monitor("test", MonitorNull())
            s.log_result(this_logger)
        mock_method.assert_not_called()

        with patch.object(logger.Logger, "save_result2") as mock_method:
            this_logger = logger.Logger({"groups": "nondefault"})
            s = SimpleMonitor()
            s.add_monitor("test", MonitorNull("unnamed", {"group": "nondefault"}))
            s.log_result(this_logger)
        mock_method.assert_called_once()


class TestFileLogger(unittest.TestCase):
    @freeze_time("2020-04-18 12:00+00:00")
    def test_file_append(self):
        temp_logfile = tempfile.mkstemp()[1]
        with open(temp_logfile, "w") as fh:
            fh.write("the first line\n")
        file_logger = FileLogger({"filename": temp_logfile, "buffered": False})
        monitor = MonitorNull()
        monitor.run_test()
        file_logger.save_result2("null", monitor)
        self.assertTrue(os.path.exists(temp_logfile))
        ts = str(int(time.time()))
        with open(temp_logfile, "r") as fh:
            self.assertEqual(fh.readline().strip(), "the first line")
            self.assertEqual(
                fh.readline().strip(), "{} simplemonitor starting".format(ts)
            )
            self.assertEqual(fh.readline().strip(), "{} null: ok (0.000s)".format(ts))
        os.unlink(temp_logfile)

    @freeze_time("2020-04-18 12:00+01:00")
    def test_file_nonutc(self):
        temp_logfile = tempfile.mkstemp()[1]
        file_logger = FileLogger({"filename": temp_logfile, "buffered": False})
        monitor = MonitorNull()
        monitor.run_test()
        file_logger.save_result2("null", monitor)
        self.assertTrue(os.path.exists(temp_logfile))
        ts = str(int(time.time()))
        with open(temp_logfile, "r") as fh:
            self.assertEqual(
                fh.readline().strip(), "{} simplemonitor starting".format(ts)
            )
            self.assertEqual(fh.readline().strip(), "{} null: ok (0.000s)".format(ts))
        os.unlink(temp_logfile)

    @freeze_time("2020-04-18 12:00+00:00")
    def test_file_utc_iso(self):
        temp_logfile = tempfile.mkstemp()[1]
        file_logger = FileLogger(
            {"filename": temp_logfile, "buffered": False, "dateformat": "iso8601"}
        )
        monitor = MonitorNull()
        monitor.run_test()
        file_logger.save_result2("null", monitor)
        self.assertTrue(os.path.exists(temp_logfile))
        ts = str(int(time.time()))
        with open(temp_logfile, "r") as fh:
            self.assertEqual(
                fh.readline().strip(),
                "2020-04-18 12:00:00+00:00 simplemonitor starting".format(ts),
            )
            self.assertEqual(
                fh.readline().strip(),
                "2020-04-18 12:00:00+00:00 null: ok (0.000s)".format(ts),
            )
        os.unlink(temp_logfile)

    @freeze_time("2020-04-18 12:00+01:00")
    def test_file_nonutc_iso_utctz(self):
        temp_logfile = tempfile.mkstemp()[1]
        file_logger = FileLogger(
            {"filename": temp_logfile, "buffered": False, "dateformat": "iso8601"}
        )
        monitor = MonitorNull()
        monitor.run_test()
        file_logger.save_result2("null", monitor)
        self.assertTrue(os.path.exists(temp_logfile))
        ts = str(int(time.time()))
        with open(temp_logfile, "r") as fh:
            self.assertEqual(
                fh.readline().strip(),
                "2020-04-18 11:00:00+00:00 simplemonitor starting".format(ts),
            )
            self.assertEqual(
                fh.readline().strip(),
                "2020-04-18 11:00:00+00:00 null: ok (0.000s)".format(ts),
            )
        os.unlink(temp_logfile)

    @freeze_time("2020-04-18 12:00+01:00")
    def test_file_nonutc_iso_nonutctz(self):
        temp_logfile = tempfile.mkstemp()[1]
        file_logger = FileLogger(
            {
                "filename": temp_logfile,
                "buffered": False,
                "dateformat": "iso8601",
                "tz": "Europe/Warsaw",
            }
        )
        monitor = MonitorNull()
        monitor.run_test()
        file_logger.save_result2("null", monitor)
        self.assertTrue(os.path.exists(temp_logfile))
        ts = str(int(time.time()))
        with open(temp_logfile, "r") as fh:
            self.assertEqual(
                fh.readline().strip(),
                "2020-04-18 13:00:00+02:00 simplemonitor starting".format(ts),
            )
            self.assertEqual(
                fh.readline().strip(),
                "2020-04-18 13:00:00+02:00 null: ok (0.000s)".format(ts),
            )
        os.unlink(temp_logfile)
