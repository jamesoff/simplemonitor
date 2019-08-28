# coding=utf-8

from .monitor import Monitor
import fabric


class RemoteMonitor(Monitor):
    """An abstract class used for remote ssh monitoring"""

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)

        self._remote_host = Monitor.get_config_option(config_options, "remote_to", required=True)
        self._port = Monitor.get_config_option(config_options, "port", required=False, required_type="int", default=22)

        self._user = Monitor.get_config_option(config_options, "user", required=True)
        # TODO: Add support for ssh key authentication
        self._password = Monitor.get_config_option(config_options, "password", required=True)

        self._connection = None

    @property
    def remote_host(self) -> str:
        return self._remote_host

    @remote_host.setter
    def remote_host(self, remote_host: str):
        self._remote_host = remote_host

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

    def prepare_test(self):
        self._connection = fabric.Connection(host=self.host, user=self.user, port=self.port, connect_kwargs={
            'password': self.password
        })

    def clean_up_test(self):
        if isinstance(self._connection, fabric.Connection):
            self._connection.close()

    def run_test(self):
        """Override this method to perform the test."""
        raise NotImplementedError

    def get_params(self):
        return self.remote_host, self.port, self.user, self.password

