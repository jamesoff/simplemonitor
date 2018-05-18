# coding=utf-8
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

    def describe(self):
        """Explain what this logger does.
        We don't throw NotImplementedError here as it won't show up until something breaks,
        and we don't want to randomly die then."""
        return "(Logger did not write an auto-biography.)"

    def __str__(self):
        return self.describe()
