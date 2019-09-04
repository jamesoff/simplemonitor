from .remote_monitor import RemoteMonitor
from .monitor import register
import re


@register
class RemoteServiceMonitor(RemoteMonitor):
    type = "remoteservice"

    def __init__(self, name, config_options):
        RemoteMonitor.__init__(self, name, config_options)

        self._service = RemoteMonitor.get_config_option(config_options, 'service', required=True)
        self._svc_cmd = RemoteMonitor.get_config_option(config_options, 'svc_cmd', required=False, default='service',
                                                        allowed_values=['chkconfig', 'service'])

    def run_test(self):
        if self.is_service_up():
            return self.record_success()

        return self.record_fail('service {} is down'.format(self.service))

    @property
    def service(self) -> str:
        return self._service

    @property
    def svc_cmd(self) -> str:
        return self._svc_cmd

    def is_service_up(self) -> bool:
        if self.svc_cmd == 'service':
            return self.is_service_up_service()
        elif self.svc_cmd == 'chkconfig':
            return self.is_service_up_chkconfig()
        else:
            raise AssertionError('Unexpected service command: {}'.format(self.svc_cmd))

    def is_service_up_service(self) -> bool:
        response = self.connection.run('service {} status'.format(self.service), warn=True, hide=True)
        return response.return_code == 0

    def is_service_up_chkconfig(self) -> bool:
        response = self.connection.run('chkconfig {}'.format(self.service), warn=True, hide=True)
        # should return a line in this format: raw  off
        if response.return_code != 0:
            return False
        lines = response.stdout.splitlines()
        if len(lines) != 1:
            raise AssertionError('Unexpected chkconfig output: {}'.format(response.stdout))

        # Regular expression: [start of line][text without space][1 or more spaces][text without space][end of line]
        matches = re.findall(r'^([^\s]+)\s+([^\s]+)$', lines[0])
        if len(matches) != 1 or len(matches[0]) != 2:
            raise AssertionError('Unexpected chkconfig output: {}'.format(response.stdout))
        service_name = matches[0][0]
        service_status = matches[0][1]

        if service_name != self.service:
            raise AssertionError('Unexpected chkconfig output: {}'.format(response.stdout))

        return service_status == 'on'

    def describe(self):
        pass

    def get_params(self):
        return super(RemoteServiceMonitor, self).get_params() + (self.service, self.svc_cmd)
