import unittest
import datetime
import Alerters.alerter


class TestAlerter(unittest.TestCase):

    def test_groups(self):
        config_options = {'groups': 'a,b,c'}
        a = Alerters.alerter.Alerter(config_options)
        self.assertEqual(['a', 'b', 'c'], a.groups)

    def test_times_always(self):
        config_options = {'times_type': 'always'}
        a = Alerters.alerter.Alerter(config_options)
        self.assertEqual(a.times_type, 'always')
        self.assertEqual(a.time_info, [None, None])

    def test_times_only(self):
        config_options = {
            'times_type': 'only',
            'time_lower': '10:00',
            'time_upper': '11:00'
        }
        a = Alerters.alerter.Alerter(config_options)
        self.assertEqual(a.times_type, 'only')
        self.assertEqual(a.time_info, [
            datetime.time(10, 00), datetime.time(11, 00)
        ])
