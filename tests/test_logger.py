# type: ignore
import unittest
from unittest.mock import patch

from simplemonitor.Loggers import logger
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
