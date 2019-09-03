from .remote_monitor import RemoteMonitor
from .monitor import register


@register
class RemoteServiceMonitor(RemoteMonitor):
    type = "remoteservice"

    def __init__(self, name, config_options):
        RemoteMonitor.__init__(self, name, config_options)

        self._service = RemoteMonitor.get_config_option(config_options, 'service', required=True)

    def run_test(self):
        response = self.connection.run('service {} status'.format(self.service), warn=True, hide=True)
        if response.return_code == 0:
            return self.record_success()

        return self.record_fail('service {} status exit code {} ({})'.format(
            self.service,
            response.return_code,
            response.stderr))

    @property
    def service(self) -> str:
        return self._service

    def describe(self):
        pass

    def get_params(self):
        return super(RemoteServiceMonitor, self).get_params() + (self.service,)
