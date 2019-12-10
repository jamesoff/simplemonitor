import os
import unittest

import envconfig

os.environ["TEST_VALUE"] = "test1"


class TestEnvConfig(unittest.TestCase):
    def test_EnvConfig(self):
        config = envconfig.EnvironmentAwareConfigParser()
        config.read("tests/monitor-env.ini")
        self.assertEqual(config.get("monitor", "monitors"), "tests/monitors-test1.ini")

    def test_EnvConfigKey(self):
        config = envconfig.EnvironmentAwareConfigParser()
        config.read("tests/monitor-env.ini")
        self.assertEqual(config.get("monitor-test1", "monitors"), "hello")
