import subprocess
import shlex

from alerter import Alerter


class ExecuteAlerter(Alerter):
    """Execute an external command when a monitor fails or recovers."""

    def __init__(self, config_options):
        Alerter.__init__(self, config_options)

        # config options
        # fail command string
        # recover command string

        if 'fail_command' in config_options:
            self.fail_command = config_options['fail_command']
        else:
            self.fail_command = None

        if 'success_command' in config_options:
            self.success_command = config_options['success_command']
        else:
            self.success_command = None

        if 'catchup_command' in config_options:
            self.catchup_command = config_options['catchup_command']

    def send_alert(self, name, monitor):
        type = self.should_alert(monitor)
        command = None
        (days, hours, minutes, seconds) = self.get_downtime(monitor)
        if monitor.is_remote():
            host = monitor.running_on
        else:
            host = self.hostname

        if type == "":
            return
        elif type == "failure":
            command = self.fail_command
        elif type == "success":
            command = self.success_command
        elif type == "catchup":
            if catchup_command == 'fail_command':
                command = self.fail_command
        else:
            print "Unknown alert type %s" % type
            return

        if command is None:
            return

        command = command.format(
            hostname=host,
            name=name,
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            failed_at=self.format_datetime(monitor.first_failure_time()),
            virtual_fail_count=monitor.virtual_fail_count(),
            info=monitor.get_result(),
            description=monitor.describe()
        )

        if not self.dry_run:
            if self.debug:
                print "About to execute command:", command
            try:
                subprocess.call(shlex.split(command))
            except Exception, e:
                print "Exception encountered running command:", command
                print e
            if self.debug:
                print "Command has finished."
        else:
            print "Would run command: %s" % command
