import unittest
import Monitors.remote_mount
from tests.test_remote_monitor import TestRemoteMonitor

from Monitors.monitor import MonitorConfigurationError


class TestRemoteMountMonitors(unittest.TestCase):

    remote_monitor_config = {
        "remote_host": "1.2.3.4",
        "user": "root",
        "port": 22,
        "password": "password123"
    }

    def get_config(self, options):
        config = dict(self.remote_monitor_config)
        config.update(options)
        return config

    def test_RemoteMount_brokenConfigOne(self):
        config_options = self.get_config({"free_space": "-1%"})
        with self.assertRaises(MonitorConfigurationError):
            Monitors.remote_mount.RemoteMountMonitor("test", config_options)

    def test_RemoteMount_brokenConfigTwo(self):
        config_options = self.get_config({"free_space": "-1"})
        with self.assertRaises(MonitorConfigurationError):
            Monitors.remote_mount.RemoteMountMonitor("test", config_options)

    def test_RemoteMount_brokenConfigThree(self):
        config_options = self.get_config({"free_space": "101%"})
        with self.assertRaises(MonitorConfigurationError):
            Monitors.remote_mount.RemoteMountMonitor("test", config_options)

    def test_RemoteMount_correctConfigOne(self):
        config_options = self.get_config({})
        m = Monitors.remote_mount.RemoteMountMonitor("test", config_options)
        self.assertIsInstance(m, Monitors.remote_mount.RemoteMountMonitor)

    def test_RemoteMount_correctConfigTwo(self):
        config_options = self.get_config({"free_space": "1"})
        m = Monitors.remote_mount.RemoteMountMonitor("test", config_options)
        self.assertIsInstance(m, Monitors.remote_mount.RemoteMountMonitor)

    # @staticmethod
    # def mock_connection(stdout, stderr):
    #     connection = Mock()
    #     connection.open = lambda *args, **kwargs: None
    #     result = Mock()
    #     result.stdout = stdout
    #     result.stderr = stderr
    #     connection.run = lambda *args, **kwargs: result
    #
    #     return connection
    #
    # def test_mockConnection(self):
    #     expected_stdout = "command stdout"
    #     expected_stderr = "command stderr"
    #     connection = self.mock_connection(stdout=expected_stdout, stderr=expected_stderr)
    #     result = connection.run('command')
    #     self.assertEqual(result.stdout, expected_stdout)
    #     self.assertEqual(result.stderr, expected_stderr)

    def test_RemoteMount_getMounts(self):
        config_options = self.get_config({"free_space": "1%"})
        m = Monitors.remote_mount.RemoteMountMonitor("test", config_options)
        m._connection = TestRemoteMonitor.mock_connection(
            stderr="",
            stdout="""Filesystem     Type     Inodes IUsed   IFree IUse% 1K-blocks    Used    Avail Use% File Mounted on
overlay        overlay 3907584 44516 3863068    2%  61255652 2135556 55978764   4% -    /
tmpfs          tmpfs    255876    16  255860    1%     65536       0    65536   0% -    /dev""")
        mounts = m.get_mounts()
        self.assertEqual(len(mounts), 2)
        self.assertEqual(mounts[0].get("Use%"), 4)
        self.assertEqual(mounts[1].get("Use%"), 0)

        m._connection = TestRemoteMonitor.mock_connection(
            stderr="",
            stdout="Filesystem     Type     Inodes IUsed   IFree IUse% "
                   "1K-blocks    Used    Avail Use% File Mounted on")
        mounts = m.get_mounts()
        self.assertEqual(len(mounts), 0)

        m._connection = TestRemoteMonitor.mock_connection(
            stderr="",
            stdout="""Filesystem      Inodes IUsed   IFree IUse% 1K-blocks    Used    Avail Use% File Mounted on
overlay        3907584 44516 3863068    2%  61255652 2135556 55978764   4% -    /
tmpfs           255876    16  255860    1%     65536       0    65536   0% -    /dev""")
        mounts = m.get_mounts()
        self.assertEqual(len(mounts), 0)

        m._connection = TestRemoteMonitor.mock_connection(
            stderr="This is an error",
            stdout="""Filesystem     Type     Inodes IUsed   IFree IUse% 1K-blocks    Used    Avail Use% File Mounted on
overlay        overlay 3907584 44516 3863068    2%  61255652 2135556 55978764   4% -    /
mpfs          tmpfs    255876    16  255860    1%     65536       0    65536   0% -    /dev""")

        mounts = m.get_mounts()
        self.assertEqual(len(mounts), 0)

    def test_RemoteMount_percent(self):
        config_options = self.get_config({"free_space": "1%"})
        m = Monitors.remote_mount.RemoteMountMonitor("test", config_options)
        m._connection = TestRemoteMonitor.mock_connection(
            stderr="",
            stdout="""Filesystem     Type     Inodes IUsed   IFree IUse% 1K-blocks    Used    Avail Use% File Mounted on
overlay        overlay 3907584 44516 3863068    2%  61255652 2135556 55978764   4% -    /
tmpfs          tmpfs    255876    16  255860    1%     65536       0    65536   0% -    /dev""")
        m.run_test()
        self.assertTrue(m.test_success())

        config_options = self.get_config({"free_space": "100%"})
        m = Monitors.remote_mount.RemoteMountMonitor("test", config_options)
        m._connection = TestRemoteMonitor.mock_connection(
            stderr="",
            stdout="""Filesystem     Type     Inodes IUsed   IFree IUse% 1K-blocks    Used    Avail Use% File Mounted on
overlay        overlay 3907584 44516 3863068    2%  61255652 2135556 55978764   4% -    /
tmpfs          tmpfs    255876    16  255860    1%     65536       0    65536   0% -    /dev""")
        m.run_test()
        self.assertFalse(m.test_success())

    def test_RemoteMount_size(self):
        config_options = self.get_config({"free_space": "1mb"})
        m = Monitors.remote_mount.RemoteMountMonitor("test", config_options)
        m._connection = TestRemoteMonitor.mock_connection(
            stderr="",
            stdout="""Filesystem     Type     Inodes IUsed   IFree IUse% 1K-blocks    Used      Avail Use% File Mounted on
overlay        overlay 3907584 44516 3863068    2%  61255652 2135556   55978764   4% -    /
tmpfs          tmpfs    255876    16  255860    1%     65536       0    6553600   0% -    /dev""")
        m.run_test()
        self.assertTrue(m.test_success())

        config_options = self.get_config({"free_space": "200gb"})
        m = Monitors.remote_mount.RemoteMountMonitor("test", config_options)
        m._connection = TestRemoteMonitor.mock_connection(
            stderr="",
            stdout="""Filesystem     Type     Inodes IUsed   IFree IUse% 1K-blocks    Used    Avail Use% File Mounted on
overlay        overlay 3907584 44516 3863068    2%  61255652 2135556 55978764   4% -    /
tmpfs          tmpfs    255876    16  255860    1%     65536       0    65536   0% -    /dev""")
        m.run_test()
        self.assertFalse(m.test_success())

    def test_RemoteMount_get_params(self):
        config_options = self.get_config({"free_space": "10%"})
        m = Monitors.remote_mount.RemoteMountMonitor("test", config_options)
        self.assertTupleEqual(m.get_params(), ("1.2.3.4", 22, "root", "password123", "10%"))


if __name__ == "__main__":
    unittest.main()
