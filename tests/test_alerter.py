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

    def test_times_not(self):
        config_options = {
            'times_type': 'not',
            'time_lower': '10:00',
            'time_upper': '11:00'
        }
        a = Alerters.alerter.Alerter(config_options)
        self.assertEqual(a.times_type, 'not')
        self.assertEqual(a.time_info, [
            datetime.time(10, 00), datetime.time(11, 00)
        ])

    def test_times_broken(self):
        config_options = {
            'times_type': 'fake',
            'time_lower': '10:00',
            'time_upper': '11:00'
        }
        with self.assertRaises(RuntimeError):
            Alerters.alerter.Alerter(config_options)

    def test_days(self):
        config_options = {
            'days': '0,1,4'
        }
        a = Alerters.alerter.Alerter(config_options)
        self.assertEqual(a.days, [0, 1, 4])

    def test_delay(self):
        config_options = {
            'delay': '1'
        }
        a = Alerters.alerter.Alerter(config_options)
        self.assertEqual(a.delay_notification, True)

    def test_dryrun(self):
        config_options = {
            'dry_run': '1'
        }
        a = Alerters.alerter.Alerter(config_options)
        self.assertEqual(a.dry_run, True)

    def test_oohrecovery(self):
        config_otions = {
            'ooh_recovery': '1'
        }
        a = Alerters.alerter.Alerter(config_otions)
        self.assertEqual(a.ooh_recovery, True)

    def test_dependencies(self):
        config_options = {
            'depend': 'a,b,c'
        }
        a = Alerters.alerter.Alerter(config_options)
        self.assertEqual(a.dependencies, ['a', 'b', 'c'], 'Alerter did not store dependencies')
        self.assertEqual(a.check_dependencies(['d', 'e']), None, 'Alerter thinks a dependency failed')
        self.assertEqual(a.check_dependencies(['a']), False, 'Alerter did not notice a dependency failed')
