# type: ignore
import os.path
import socket
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from freezegun import freeze_time

from simplemonitor.Loggers import logger
from simplemonitor.Loggers.file import FileLogger, FileLoggerNG, HTMLLogger
from simplemonitor.Monitors.monitor import MonitorFail, MonitorNull
from simplemonitor.simplemonitor import SimpleMonitor
from simplemonitor.version import VERSION


class TestLogger(unittest.TestCase):
    def test_default(self):
        config_options = {}
        test_logger = logger.Logger(config_options)
        self.assertEqual(
            test_logger.dependencies, [], "logger did not set default dependencies"
        )

    def test_dependencies(self):
        config_options = {"depend": "a, b"}
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
            s = SimpleMonitor(Path("tests/monitor-empty.ini"))
            s.add_monitor("test", MonitorNull())
            s.log_result(this_logger)
        mock_method.assert_not_called()

        with patch.object(logger.Logger, "save_result2") as mock_method:
            this_logger = logger.Logger({"groups": "nondefault"})
            s = SimpleMonitor(Path("tests/monitor-empty.ini"))
            s.add_monitor("test", MonitorNull("unnamed", {"group": "nondefault"}))
            s.log_result(this_logger)
        mock_method.assert_called_once()

    def test_skip_group_logger(self):
        with patch.object(logger.Logger, "save_result2") as mock_method:
            this_logger = logger.Logger({"groups": "test"})
            s = SimpleMonitor(Path("tests/monitor-empty.ini"))
            s.add_monitor("test", MonitorNull("unnamed", {}))
            s.log_result(this_logger)
        mock_method.assert_not_called()

    def test_skip_group_monitor(self):
        with patch.object(logger.Logger, "save_result2") as mock_method:
            this_logger = logger.Logger({})
            s = SimpleMonitor(Path("tests/monitor-empty.ini"))
            s.add_monitor("test", MonitorNull("unnamed", {"group": "test"}))
            s.log_result(this_logger)
        mock_method.assert_not_called()

    def test_groups_match(self):
        with patch.object(logger.Logger, "save_result2") as mock_method:
            this_logger = logger.Logger({"groups": "test"})
            s = SimpleMonitor(Path("tests/monitor-empty.ini"))
            s.add_monitor("test", MonitorNull("unnamed", {"group": "test"}))
            s.log_result(this_logger)
        mock_method.assert_called_once()

    def test_groups_multi_match(self):
        with patch.object(logger.Logger, "save_result2") as mock_method:
            this_logger = logger.Logger({"groups": "test1, test2"})
            s = SimpleMonitor(Path("tests/monitor-empty.ini"))
            s.add_monitor("test", MonitorNull("unnamed", {"group": "test1"}))
            s.log_result(this_logger)
        mock_method.assert_called_once()

    def test_groups_all_match(self):
        with patch.object(logger.Logger, "save_result2") as mock_method:
            this_logger = logger.Logger({"groups": "_all"})
            s = SimpleMonitor(Path("tests/monitor-empty.ini"))
            s.add_monitor("test", MonitorNull("unnamed", {"group": "test1"}))
            s.log_result(this_logger)
        mock_method.assert_called_once()

    def test_heartbeat_off(self):
        with patch.object(logger.Logger, "save_result2") as mock_method:
            this_logger = logger.Logger({})
            s = SimpleMonitor(Path("tests/monitor-empty.ini"))
            s.add_monitor("test", MonitorNull("unnamed"))
            s.add_logger("test", this_logger)
            s.run_loop()
            s.run_loop()
            self.assertEqual(mock_method.call_count, 2)

    def test_heartbeat_on(self):
        with patch.object(logger.Logger, "save_result2") as mock_method:
            this_logger = logger.Logger({"heartbeat": 1})
            this_monitor = MonitorNull("unnamed", {"gap": 10})
            s = SimpleMonitor(Path("tests/monitor-empty.ini"))
            s.add_monitor("test", this_monitor)
            s.add_logger("test", this_logger)
            s.run_loop()
            s.run_loop()
            mock_method.assert_called_once()

    def test_reset_monitor(self):
        s = SimpleMonitor(Path("tests/monitor-empty.ini"))
        s.add_monitor("monitor1", MonitorNull("monitor1"))
        s.add_monitor("monitor2", MonitorNull("monitor2", {"depend": "monitor1"}))
        s.run_loop()
        self.assertTrue(s.monitors["monitor1"].ran_this_time)
        self.assertTrue(s.monitors["monitor2"].ran_this_time)
        self.assertEqual(s.monitors["monitor2"].remaining_dependencies, [])
        s.reset_monitors()
        self.assertFalse(s.monitors["monitor1"].ran_this_time)
        self.assertFalse(s.monitors["monitor2"].ran_this_time)
        self.assertEqual(s.monitors["monitor2"].remaining_dependencies, ["monitor1"])


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
        try:
            os.unlink(temp_logfile)
        except PermissionError:
            # Windows won't remove a file which is in use
            pass

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
        try:
            os.unlink(temp_logfile)
        except PermissionError:
            # Windows won't remove a file which is in use
            pass

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
        with open(temp_logfile, "r") as fh:
            self.assertEqual(
                fh.readline().strip(),
                "2020-04-18 12:00:00+00:00 simplemonitor starting",
            )
            self.assertEqual(
                fh.readline().strip(),
                "2020-04-18 12:00:00+00:00 null: ok (0.000s)",
            )
        try:
            os.unlink(temp_logfile)
        except PermissionError:
            # Windows won't remove a file which is in use
            pass

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
        with open(temp_logfile, "r") as fh:
            self.assertEqual(
                fh.readline().strip(),
                "2020-04-18 11:00:00+00:00 simplemonitor starting",
            )
            self.assertEqual(
                fh.readline().strip(),
                "2020-04-18 11:00:00+00:00 null: ok (0.000s)",
            )
        try:
            os.unlink(temp_logfile)
        except PermissionError:
            # Windows won't remove a file which is in use
            pass

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
        with open(temp_logfile, "r") as fh:
            self.assertEqual(
                fh.readline().strip(),
                "2020-04-18 13:00:00+02:00 simplemonitor starting",
            )
            self.assertEqual(
                fh.readline().strip(),
                "2020-04-18 13:00:00+02:00 null: ok (0.000s)",
            )
        try:
            os.unlink(temp_logfile)
        except PermissionError:
            # Windows won't remove a file which is in use
            pass


class TestLogFileNG(unittest.TestCase):
    @freeze_time("2020-04-18 12:00+00:00")
    def test_file_time(self):
        temp_logfile = tempfile.mkstemp()[1]
        file_logger = FileLoggerNG({"filename": temp_logfile, "rotation_type": "time"})
        monitor = MonitorNull()
        monitor.run_test()
        file_logger.save_result2("null", monitor)
        self.assertTrue(os.path.exists(temp_logfile))
        ts = str(int(time.time()))
        with open(temp_logfile, "r") as fh:
            self.assertEqual(
                fh.readline().strip(), "{} null: ok (0.000s) ()".format(ts)
            )
        try:
            os.unlink(temp_logfile)
        except PermissionError:
            # Windows won't remove a file which is in use
            pass

    @freeze_time("2020-04-18 12:00+00:00")
    def test_file_size(self):
        temp_logfile = tempfile.mkstemp()[1]
        file_logger = FileLoggerNG(
            {"filename": temp_logfile, "rotation_type": "size", "max_bytes": "1K"}
        )
        monitor = MonitorNull()
        monitor.run_test()
        file_logger.save_result2("null", monitor)
        self.assertTrue(os.path.exists(temp_logfile))
        ts = str(int(time.time()))
        with open(temp_logfile, "r") as fh:
            self.assertEqual(
                fh.readline().strip(), "{} null: ok (0.000s) ()".format(ts)
            )
        try:
            os.unlink(temp_logfile)
        except PermissionError:
            # Windows won't remove a file which is in use
            pass

    @freeze_time("2020-04-18 12:00+00:00")
    def test_file_only_failures(self):
        temp_logfile = tempfile.mkstemp()[1]
        file_logger = FileLoggerNG(
            {
                "filename": temp_logfile,
                "rotation_type": "size",
                "max_bytes": "1K",
                "only_failures": "1",
                "dateformat": "iso8601",
            }
        )
        monitor = MonitorNull()
        monitor.run_test()
        monitor2 = MonitorFail("fail", {})
        monitor2.run_test()
        file_logger.save_result2("null", monitor)
        file_logger.save_result2("fail", monitor2)
        self.assertTrue(os.path.exists(temp_logfile))
        ts = "2020-04-18 12:00:00+00:00"
        with open(temp_logfile, "r") as fh:
            self.assertEqual(
                fh.readline().strip(),
                "{} fail: failed since {}; VFC=1 ({}) (0.000s)".format(
                    ts, ts, monitor2.last_result
                ),
            )
        try:
            os.unlink(temp_logfile)
        except PermissionError:
            # Windows won't remove a file which is in use
            pass

    def test_file_missing_rotation(self):
        with self.assertRaises(ValueError):
            _ = FileLoggerNG({"filename": "something.log"})

    def test_file_missing_bytes(self):
        with self.assertRaises(ValueError):
            _ = FileLoggerNG({"filename": "something.log", "rotation_type": "size"})

    def test_file_bad_rotation(self):
        with self.assertRaises(ValueError):
            _ = FileLoggerNG({"filename": "something.log", "rotation_type": "magic"})


class TestHTMLLogger(unittest.TestCase):
    def setUp(self) -> None:
        self.html_dir = tempfile.mkdtemp()
        print(f"writing html tests to {self.html_dir}")

    @freeze_time("2020-04-18 12:00:00+00:00")
    def _write_html(self, logger_options: dict = None) -> str:
        if logger_options is None:
            logger_options = {}
        with patch.object(socket, "gethostname", return_value="fake_hostname.local"):
            temp_htmlfile = tempfile.mkstemp()[1]
            logger_options.update({"filename": temp_htmlfile, "folder": self.html_dir})
            html_logger = HTMLLogger(logger_options)
            monitor1 = MonitorNull(config_options={"gps": "52.01,1.01"})
            monitor2 = MonitorFail("fail", {"gps": "52.02,1.02"})
            monitor3 = MonitorFail("disabled", {"enabled": 0, "gps": "52.03,1.03"})
            monitor1.run_test()
            monitor2.run_test()
            html_logger.start_batch()
            html_logger.save_result2("null", monitor1)
            html_logger.save_result2("fail", monitor2)
            html_logger.save_result2("disabled", monitor3)
            html_logger.end_batch()
        print(temp_htmlfile)
        return temp_htmlfile

    def _compare_files(self, test_file, golden_file):
        self.maxDiff = 6200
        with open(test_file) as test_fh, open(golden_file) as golden_fh:
            golden_data = golden_fh.read()
            golden_data = golden_data.replace("__VERSION__", VERSION)
            self.assertMultiLineEqual(golden_data, test_fh.read())

    def test_html(self):
        test_file = self._write_html()
        golden_file = "tests/html/test1.html"
        self._compare_files(test_file, golden_file)

    def test_html_tz(self):
        test_file = self._write_html({"tz": "Europe/Warsaw"})
        golden_file = "tests/html/test2.html"
        self._compare_files(test_file, golden_file)

    def test_html_map(self):
        test_file = self._write_html(
            {"map_start": [52, 1, 12], "map": 1, "map_token": "secret_token"}
        )
        golden_file = "tests/html/map1.html"
        self._compare_files(test_file, golden_file)

    def test_config_start(self):
        with self.assertRaises(RuntimeError):
            _ = HTMLLogger({"map": "1", "filename": "something"})
        with self.assertRaises(RuntimeError):
            _ = HTMLLogger({"map": "1", "map_start": "1, 2", "filename": "something"})
