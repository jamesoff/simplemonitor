# type: ignore
import unittest

from simplemonitor.Loggers import logger


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
