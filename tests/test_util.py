import unittest
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
