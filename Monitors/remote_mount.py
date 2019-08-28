from .remote_monitor import RemoteMonitor
from .monitor import register
import re


def _size_string_to_bytes(size: str) -> int:
    """
    Converts a human readable size to bytes
    :param size: The size to convert (in the format [number][size unit])
    :return: The given size in bytes
    """
    matches = re.findall(r'^(\d+)(.*?)$', size.replace(' ', '').upper())
    if matches is None or len(matches) != 1 or len(matches[0]) != 2:
        return None

    value = int(matches[0][0])
    unit = matches[0][1]

    _size_bytes = None
    if unit == 'TB':
        _size_bytes = value * 1024 * 1024 * 1024 * 1024
    elif unit == 'GB':
        _size_bytes = value * 1024 * 1024 * 1024
    elif unit == 'MB':
        _size_bytes = value * 1024 * 1024
    elif unit == 'KB':
        _size_bytes = value * 1024
    elif unit in ['BYTES', 'BYTE', 'B', '']:
        _size_bytes = value

    return _size_bytes


@register
class RemoteMountMonitor(RemoteMonitor):
    type = "remotemount"

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
        # TODO: Stop stdout of command to be printed
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

