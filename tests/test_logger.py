import unittest
import Loggers.logger


class TestLogger(unittest.TestCase):
    def test_default(self):
        config_options = {}
        logger = Loggers.logger.Logger(config_options)
        self.assertEqual(
            logger.dependencies, [], "logger did not set default dependencies"
        )

    def test_dependencies(self):
        config_options = {"depend": ["a", "b"]}
        logger = Loggers.logger.Logger(config_options)
        self.assertEqual(
            logger.dependencies,
            ["a", "b"],
            "logger did not set dependencies to given list",
        )
        with self.assertRaises(TypeError):
            logger.dependencies = "moo"
        logger.dependencies = ["b", "c"]
        self.assertEqual(
            logger.check_dependencies(["a"]),
            True,
            "logger thought a dependency had failed",
        )
        self.assertEqual(
            logger.connected, True, "logger did not think it was connected"
        )
        self.assertEqual(
            logger.check_dependencies(["a", "b"]),
            False,
            "logger did not think a dependency failed",
        )
        self.assertEqual(logger.connected, False, "logger thought it was connected")
