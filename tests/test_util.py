# type: ignore
import datetime
import unittest

from simplemonitor import util


class TestUtil(unittest.TestCase):
    def test_Config(self):
        config_options = {
            "test_string": "a string",
            "test_int": "3",
            "test_[int]": "1,2, 3",
            "test_[str]": "a, b,c",
            "test_bool1": "1",
            "test_bool2": "yes",
            "test_bool3": "true",
            "test_bool4": "0",
        }
        self.assertEqual(
            util.get_config_option(config_options, "test_string"), "a string"
        )
        self.assertEqual(
            util.get_config_option(config_options, "test_int", required_type="int"), 3
        )
        self.assertEqual(
            util.get_config_option(config_options, "test_[int]", required_type="[int]"),
            [1, 2, 3],
        )
        self.assertEqual(
            util.get_config_option(config_options, "test_[str]", required_type="[str]"),
            ["a", "b", "c"],
        )
        for bool_test in list(range(1, 4)):
            self.assertEqual(
                util.get_config_option(
                    config_options,
                    "test_bool{0}".format(bool_test),
                    required_type="bool",
                ),
                True,
            )
        self.assertEqual(
            util.get_config_option(config_options, "test_bool4", required_type="bool"),
            False,
        )
        with self.assertRaises(ValueError):
            util.get_config_option(["not a dict"], "")
        with self.assertRaises(ValueError):
            util.get_config_option(config_options, "missing_value", required=True)
        with self.assertRaises(ValueError):
            util.get_config_option(config_options, "test_string", required_type="int")
        with self.assertRaises(ValueError):
            util.get_config_option(config_options, "test_string", required_type="float")
        with self.assertRaises(ValueError):
            util.get_config_option(
                config_options, "test_int", required_type="int", minimum=4
            )
        with self.assertRaises(ValueError):
            util.get_config_option(
                config_options, "test_int", required_type="int", maximum=2
            )
        with self.assertRaises(ValueError):
            util.get_config_option(config_options, "test_[str]", required_type="[int]")
        with self.assertRaises(ValueError):
            util.get_config_option(
                config_options,
                "test_[str]",
                required_type="[str]",
                allowed_values=["d"],
            )
        with self.assertRaises(ValueError):
            util.get_config_option(
                config_options,
                "test_string",
                allowed_values=["other string", "other other string"],
            )
        with self.assertRaises(NotImplementedError):
            util.get_config_option(
                "not a dict", "doesn't matter", exception=NotImplementedError
            )
        with self.assertRaises(ValueError):
            util.get_config_option(
                {"empty_string": ""},
                "empty_string",
                required_type="str",
                allow_empty=False,
            )

    def test_Format(self):
        self.assertEqual(util.format_datetime(None), "")
        self.assertEqual(util.format_datetime("a string"), "a string")
        self.assertEqual(
            util.format_datetime(datetime.datetime(2018, 5, 8, 13, 37, 0)),
            "2018-05-08 13:37:00",
        )


class TestUpDownTime(unittest.TestCase):
    def test_blankInit(self):
        u = util.UpDownTime()
        self.assertEqual(0, u.days, "days not defaulted to 0")
        self.assertEqual(0, u.hours, "hours not defaulted to 0")
        self.assertEqual(0, u.minutes, "minutes not defaulted to 0")
        self.assertEqual(0, u.seconds, "seconds not defaulted to 0")

    def test_givenInit(self):
        u = util.UpDownTime(1, 2, 3, 4)
        self.assertEqual(1, u.days, "days not inited to 1")
        self.assertEqual(2, u.hours, "hours not inited to 2")
        self.assertEqual(3, u.minutes, "minutes not inited to 3")
        self.assertEqual(4, u.seconds, "seconds not inited to 4")

    def test_initTimeDelta(self):
        diff = datetime.timedelta(1, 90)
        u = util.UpDownTime.from_timedelta(diff)
        self.assertEqual(1, u.days, "days not inited to 1")
        self.assertEqual(0, u.hours, "hours not inited to 0")
        self.assertEqual(1, u.minutes, "minutes not inited to 1")
        self.assertEqual(30, u.seconds, "seconds not inited to 30")

    def test_equal(self):
        u1 = util.UpDownTime(1, 2, 3, 4)
        u2 = util.UpDownTime(1, 2, 3, 4)
        self.assertEqual(u1, u2)

    def test_str(self):
        u1 = util.UpDownTime(1, 2, 3, 4)
        self.assertEqual(str(u1), "1+02:03:04")
