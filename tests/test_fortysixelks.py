# type: ignore
import unittest

from simplemonitor import util
from simplemonitor.Alerters import fortysixelks


class Test46Elks(unittest.TestCase):
    def test_46elks(self):
        config_options = {"username": "a", "password": "b", "target": "c"}
        config_options["sender"] = "ab"
        with self.assertRaises(util.AlerterConfigurationError):
            a = fortysixelks.FortySixElksAlerter(config_options=config_options)
        config_options["sender"] = "123456789012"
        a = fortysixelks.FortySixElksAlerter(config_options=config_options)
        self.assertEqual(a.sender, "12345678901")
