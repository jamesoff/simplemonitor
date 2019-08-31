from .remote_monitor import RemoteMonitor
from .monitor import register
import re
from .host import _bytes_to_size_string


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

        self.free_space = RemoteMonitor.get_config_option(config_options, 'free_space', required=False, default='1GB')

        # free space can be given as a percentage or an absolute size (i.e. 10GB)
        if '%' in self.free_space:
            self.free_space_required = int(self.free_space.replace('%', ''))
            self.free_space_unit = 'percent'
        else:
            self.free_space_required = _size_string_to_bytes(self.free_space)
            self.free_space_unit = 'byte'

    def run_test(self):
        mounts = self.get_mounts()

        failed_mounts = []

        assert self.free_space_unit in ['percent', 'byte']

        # Father all the mounts that do not have enough free space
        if self.free_space_unit == 'percent':
            for mount in mounts:
                percent_free = 100 - mount.get('Use%')
                if percent_free < self.free_space_required:
                    failed_mounts.append(mount)
        elif self.free_space_unit == 'byte':
            for mount in mounts:
                free_bytes = mount.get('Avail') - mount.get('Used')
                if free_bytes < self.free_space_required:
                    failed_mounts.append(mount)

        if not failed_mounts:
            return self.record_success()

        msg = ''
        for mount in failed_mounts:
            if msg != '':
                msg += '\n'
            mount_point = mount.get("Mounted on")
            percent_left = f'{100 - mount.get("Use%")}%'
            mount_size = _bytes_to_size_string(mount.get("Avail"))
            amount_left = _bytes_to_size_string(mount.get('Avail') - mount.get('Used'))
            msg += f'{self.host}:{mount_point} has {percent_left} free space out of {mount_size} ({amount_left} left)'
        return self.record_fail(msg)

    def describe(self):
        pass

    def get_params(self):
        return super(RemoteMountMonitor, self).get_params() + (self._free_space,)

    def get_mounts(self):
        result = self.connection.run('df --output', hide=True)
        self.monitor_logger.debug(f'stdout: {result.stdout}')
        self.monitor_logger.debug(f'stderr: {result.stderr}')
        # A sample output of the command:
        #   Filesystem     Type     Inodes IUsed   IFree IUse% 1K-blocks    Used    Avail Use% File Mounted on
        #   overlay        overlay 3907584 44516 3863068    2%  61255652 2135556 55978764   4% -    /
        #   tmpfs          tmpfs    255876    16  255860    1%     65536       0    65536   0% -    /dev
        #   tmpfs          tmpfs    255876    14  255862    1%   1023504       0  1023504   0% -    /sys/fs/cgroup
        #   shm            tmpfs    255876     1  255875    1%     65536       0    65536   0% -    /dev/shm
        #   /dev/sda1      ext4    3907584 44516 3863068    2%  61255652 2135556 55978764   4% -    /etc/hosts
        #   tmpfs          tmpfs    255876     1  255875    1%   1023504       0  1023504   0% -    /proc/acpi
        #   tmpfs          tmpfs    255876     1  255875    1%   1023504       0  1023504   0% -    /sys/firmware

        if result.stderr or not result.stdout:
            return []
        lines = str(result.stdout).splitlines()
        if len(lines) <= 1:
            return []

        mounts = []
        for index, line in enumerate(lines[1:]):
            values = re.split(r'\s+', line)
            if len(values) != 12:
                self.monitor_logger.warning(f'Invalid df --output row, expected it to have 12 values, '
                                            f'but found {len(values)} (row: {line})')
            else:
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

