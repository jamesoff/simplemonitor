import unittest
import datetime
import util


class TestUtil(unittest.TestCase):
    def test_Config(self):
        config_options = {
            'test_string': 'a string',
            'test_int': '3',
            'test_[int]': '1,2, 3',
            'test_[str]': 'a, b,c',
            'test_bool1': '1',
            'test_bool2': 'yes',
            'test_bool3': 'true',
            'test_bool4': '0'
        }
        self.assertEqual(
            util.get_config_option(
                config_options,
                'test_string'),
            'a string'
        )
        self.assertEqual(
            util.get_config_option(
                config_options,
                'test_int',
                required_type='int'),
            3
        )
        self.assertEqual(
            util.get_config_option(
                config_options,
                'test_[int]',
                required_type='[int]'),
            [1, 2, 3]
        )
        self.assertEqual(
            util.get_config_option(
                config_options,
                'test_[str]',
                required_type='[str]'),
            ['a', 'b', 'c']
        )
        for bool_test in list(range(1, 4)):
            self.assertEqual(
                util.get_config_option(
                    config_options,
                    'test_bool{0}'.format(bool_test),
                    required_type='bool'),
                True
            )
        self.assertEqual(
            util.get_config_option(
                config_options,
                'test_bool4',
                required_type='bool'),
            False
        )
        with self.assertRaises(ValueError):
            util.get_config_option(
                ['not a dict'],
                ''
            )
        with self.assertRaises(ValueError):
            util.get_config_option(
                config_options,
                'missing_value',
                required=True
            )
        with self.assertRaises(ValueError):
            util.get_config_option(
                config_options,
                'test_string',
                required_type='int'
            )
        with self.assertRaises(ValueError):
            util.get_config_option(
                config_options,
                'test_string',
                required_type='float'
            )
        with self.assertRaises(ValueError):
            util.get_config_option(
                config_options,
                'test_int',
                required_type='int',
                minimum=4
            )
        with self.assertRaises(ValueError):
            util.get_config_option(
                config_options,
                'test_int',
                required_type='int',
                maximum=2
            )
        with self.assertRaises(ValueError):
            util.get_config_option(
                config_options,
                'test_[str]',
                required_type='[int]'
            )
        with self.assertRaises(ValueError):
            util.get_config_option(
                config_options,
                'test_[str]',
                required_type='[str]',
                allowed_values=['d']
            )
        with self.assertRaises(ValueError):
            util.get_config_option(
                config_options,
                'test_string',
                allowed_values=['other string', 'other other string']
            )
        with self.assertRaises(NotImplementedError):
            util.get_config_option(
                'not a dict',
                "doesn't matter",
                exception=NotImplementedError
            )
        with self.assertRaises(ValueError):
            util.get_config_option(
                {'empty_string': ''},
                'empty_string',
                required_type='str',
                allow_empty=False
            )

    def test_Format(self):
        self.assertEqual(util.format_datetime(None), "")
        self.assertEqual(util.format_datetime("a string"), "a string")
        self.assertEqual(
            util.format_datetime(datetime.datetime(2018, 5, 8, 13, 37, 0)),
            "2018-05-08 13:37:00"
        )
