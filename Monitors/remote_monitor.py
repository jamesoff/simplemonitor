# coding=utf-8

from .monitor import Monitor, register
import fabric
from os.path import isfile


class RemoteMonitor(Monitor):
    """An abstract class used for remote ssh monitoring"""

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)

        self._host = Monitor.get_config_option(config_options, "remote_host", required=True)
        self._port = Monitor.get_config_option(config_options, "port", required=False, required_type="int", default=22)

        self._user = Monitor.get_config_option(config_options, "user", required=True)
        self._password = Monitor.get_config_option(config_options, "password", required=False, default=None)
        if self._password is None:
            self._key = Monitor.get_config_option(config_options, "key", required=True)
        else:
            self._key = Monitor.get_config_option(config_options, "key", required=False, default=None)

        if self._key is not None and not isfile(self._key):
            raise OSError('[Errno 2] No such file: {}'.format(self._key))

        self._connection = fabric.Connection(host=self.host, user=self.user, port=self.port, connect_kwargs={
            'password': self.password,
            'key_filename': self._key
        })

    @property
    def host(self) -> str:
        return self._host

    @host.setter
    def host(self, host: str):
        self._host = host

    @property
    def user(self) -> str:
        return self._user

    @user.setter
    def user(self, user: str):
        self._user = user

    @property
    def port(self) -> int:
        return self._port

    @port.setter
    def port(self, port: int):
        self._port = port

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, password: str):
        self._password = password

    @property
    def connection(self) -> fabric.Connection:
        return self._connection

    def clean_up_test(self):
        if isinstance(self._connection, fabric.Connection):
            self._connection.close()

    def run_test(self):
        """Override this method to perform the test."""
        raise NotImplementedError

    def get_params(self):
        return self.host, self.port, self.user, self.password


@register
class RemoteMonitorFail(RemoteMonitor):
    type = "remotemonitorfail"

    def run_test(self):
        self.record_fail("This monitor always fails.")


@register
class RemoteMonitorNull(RemoteMonitor):
    type = "remotemonitornull"

    def run_test(self):
        self.record_success()
