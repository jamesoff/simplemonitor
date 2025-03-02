# type: ignore
import unittest

from simplemonitor.Monitors import host


class TestHostMonitors(unittest.TestCase):
    safe_config = {"partition": "/", "limit": "10G"}

    one_KB = 1024
    one_MB = one_KB * 1024
    one_GB = one_MB * 1024
    one_TB = one_GB * 1024

    def test_DiskSpace_brokenConfigOne(self):
        config_options = {}
        with self.assertRaises(ValueError):
            host.MonitorDiskSpace("test", config_options)

    def test_DiskSpace_brokenConfigTwo(self):
        config_options = {"partition": "/"}
        with self.assertRaises(ValueError):
            host.MonitorDiskSpace("test", config_options)

    def test_DiskSpace_brokenConfigThree(self):
        config_options = {"partition": "/", "limit": "moo"}
        with self.assertRaises(ValueError):
            host.MonitorDiskSpace("test", config_options)

    def test_DiskSpace_correctConfig(self):
        m = host.MonitorDiskSpace("test", self.safe_config)
        self.assertIsInstance(m, host.MonitorDiskSpace)

    def test_DiskSpace_meta(self):
        m = host.MonitorDiskSpace("test", self.safe_config)

        self.assertEqual(
            m.describe(),
            "Checking for at least 10.00GiB free space on /",
            "Failed to verify description",
        )

        self.assertTupleEqual(
            m.get_params(), (10 * self.one_GB, "/"), "Failed to verify params"
        )

    def test_DiskSpace_free(self):
        # Hopefully our test machine has at least 1 byte free on /
        config_options = {"partition": "/", "limit": "1"}
        m = host.MonitorDiskSpace("test", config_options)
        m.run_test()
        self.assertTrue(m.test_success())

        # and hopefully it has a sensible-sized root partition
        config_options = {"partition": "/", "limit": "100000G"}
        m = host.MonitorDiskSpace("test", config_options)
        m.run_test()
        self.assertFalse(m.test_success())

    def test_DiskSpace_invalid_partition(self):
        config_options = {"partition": "moo", "limit": "1"}
        m = host.MonitorDiskSpace("test", config_options)
        m.run_test()
        self.assertFalse(m.test_success(), "Monitor did not fail")
        self.assertRegex(
            m.last_result,
            "Couldn't get free disk space",
            "Monitor did not report error correctly",
        )

    def test_DiskSpace_get_params(self):
        config_options = {"partition": "/", "limit": "1"}
        m = host.MonitorDiskSpace("test", config_options)
        self.assertTupleEqual(m.get_params(), (1, "/"))

    def test_Filestat_get_params(self):
        config_options = {"maxage": "10", "minsize": "20", "filename": "/test"}
        m = host.MonitorFileStat("test", config_options)
        self.assertTupleEqual(m.get_params(), ("/test", 20, 10))

    def test_Command_get_params(self):
        config_options = {"command": "ls /", "result_regexp": "moo", "result_max": "10"}
        m = host.MonitorCommand("test", config_options)
        self.assertTupleEqual(m.get_params(), (["ls", "/"], "moo", None, False))

        config_options = {"command": "ls /", "result_max": "10"}
        m = host.MonitorCommand("test", config_options)
        self.assertTupleEqual(m.get_params(), (["ls", "/"], "", 10, False))

        config_options = {"command": "ls /", "result_max": "10", "show_output": True}
        m = host.MonitorCommand("test", config_options)
        self.assertTupleEqual(m.get_params(), (["ls", "/"], "", 10, True))


if __name__ == "__main__":
    unittest.main()
