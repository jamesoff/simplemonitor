# coding=utf-8
import datetime
import logging

from util import get_config_option, LoggerConfigurationError


class Logger(object):
    """Abstract class basis for loggers."""

    dependencies = []

    supports_batch = False

    doing_batch = True

    batch_data = {}

    def __init__(self, config_options):
        self.name = Logger.get_config_option(
            config_options,
            '_name',
            default='unnamed'
        )
        self.logger_logger = logging.getLogger('simplemonitor.logger-' + self.name)
        self.set_dependencies(Logger.get_config_option(
            config_options,
            'depend',
            required_type='[str]',
            default=[]
        ))

    @staticmethod
    def get_config_option(config_options, key, **kwargs):
        kwargs['exception'] = LoggerConfigurationError
        return get_config_option(config_options, key, **kwargs)

    def hup(self):
        """Close and reopen our log file, if supported.

        This should be overridden where needed."""
        return

    def save_result(self):
        raise NotImplementedError

    def set_dependencies(self, dependency_list):
        """Record which monitors we depend on.
        If a monitor we depend on fails, it means we can't reach the database, so we shouldn't bother trying to write to it."""
        # TODO: Maybe cache the commands until connection returns

        self.dependencies = dependency_list

    def check_dependencies(self, failed_list):
        for dependency in failed_list:
            if dependency in self.dependencies:
                self.connected = False
                return False
        self.connected = True

    def start_batch(self):
        """We're about to start a batch."""
        if not self.supports_batch:
            return
        self.batch_data = {}
        self.doing_batch = True

    def end_batch(self):
        """We've ended a batch."""
        if not self.supports_batch:
            return
        self.process_batch()
        self.doing_batch = False

    def process_batch(self):
        """This is blank for the base class."""
        return

    def get_downtime(self, monitor):
        try:
            downtime = datetime.datetime.utcnow() - monitor.first_failure_time()
            seconds = downtime.seconds
            if seconds > 3600:
                hours = seconds / 3600
                seconds = seconds - (hours * 3600)
            else:
                hours = 0
            if seconds > 60:
                minutes = seconds / 60
                seconds = seconds - (minutes * 60)
            else:
                minutes = 0
            return (downtime.days, hours, int(minutes), int(seconds))
        except Exception:
            return (0, 0, 0, 0)

    def format_datetime(self, dt):
        """Return an isoformat()-like datetime without the microseconds."""
        if dt is None:
            return ""

        if isinstance(dt, datetime.datetime):
            dt = dt.replace(microsecond=0)
            return dt.isoformat(' ')
        else:
            return dt
