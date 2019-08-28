from .remote_monitor import RemoteMonitor
import re


class RemoteMountMonitor(RemoteMonitor):

    def __init__(self, name, config_options):
        RemoteMonitor.__init__(self, name, config_options)

        self._free_space = RemoteMonitor.get_config_option(config_options, 'freespace', required=False, default='1GB')

    def run_test(self):
        mounts = self.get_mounts()
        pass

    def describe(self):
        pass

    def get_params(self):
        return super(RemoteMountMonitor, self).get_params() + (self._free_space,)

    def get_mounts(self):
        result = self.connection.run('df --output')
        if result.stderr or not result.stdout:
            return []
        lines = str(result.stdout).splitlines()
        if len(lines) <= 1:
            return []

        mounts = []
        for index, line in enumerate(lines[1:]):
            values = re.split(r'\s+', line)
            mount = {
                'Filesystem': values[0],
                'Type': values[1],
                'Inodes': int(values[2]),
                'IUsed': int(values[3]),
                'IFree': int(values[4]),
                'IUse%': int(values[5].replace('%', '')),
                '1K-blocks': int(values[6]),
                'Used': int(values[7]),
                'Avail': int(values[8]),
                'Use%': int(values[9].replace('%', '')),
                'File': values[10],
                'Mounted on': values[11]
            }
            mounts.append(mount)
        return mounts

