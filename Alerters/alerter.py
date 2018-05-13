# coding=utf-8
"""A collection of alerters for SimpleMonitor."""

import datetime
import logging

from socket import gethostname

from util import get_config_option, AlerterConfigurationError


class Alerter:
    """Abstract class basis for alerters."""

    dependencies = []
    hostname = gethostname()
    available = False
    limit = 1
    repeat = 0

    days = list(range(0, 7))
    times_type = "always"
    time_info = [None, None]

    debug = False
    verbose = False

    dry_run = False
    groups = ['default']

    delay_notification = False
    ooh_failures = []
    # subclasses should set this to true if they support catchup notifications for delays
    support_catchup = False
    ooh_recovery = False

    type = 'unknown'

    def __init__(self, config_options=None):
        if config_options is None:
            config_options = {}
        self.alerter_logger = logging.getLogger('simplemonitor.alerter-' + self.type)
        self.available = True
        self.set_dependencies(Alerter.get_config_option(
            config_options,
            'depend',
            required_type='[str]',
            default=[]
        ))
        self.limit = Alerter.get_config_option(
            config_options,
            'limit',
            required_type='int',
            minimum=1,
            default=1
        )
        self.repeat = Alerter.get_config_option(
            config_options,
            'repeat',
            required_type='int',
            default=0,
            minimum=0
        )
        self.set_groups(Alerter.get_config_option(
            config_options,
            'groups',
            required_type='[str]',
            default=['default']
        ))
        self.times_type = Alerter.get_config_option(
            config_options,
            'times_type',
            required_type='str',
            allowed_values=['always', 'only', 'not'],
            default='always'
        )
        if self.times_type in ['only', 'not']:
            time_lower = Alerter.get_config_option(
                config_options,
                'time_lower',
                required_type='str',
                required=True
            )
            time_upper = Alerter.get_config_option(
                config_options,
                'time_upper',
                required_type='str',
                required=True
            )
            try:
                time_info = [
                    datetime.time(
                        int(time_lower.split(":")[0]),
                        int(time_lower.split(":")[1])
                    ),
                    datetime.time(
                        int(time_upper.split(":")[0]),
                        int(time_upper.split(":")[1])
                    )
                ]
                self.time_info = time_info
            except Exception:
                raise RuntimeError("error processing time limit definition")
        self.days = Alerter.get_config_option(
            config_options,
            'days',
            required_type='[int]',
            allowed_values=list(range(0, 7)),
            default=list(range(0, 7))
        )
        self.delay_notification = Alerter.get_config_option(
            config_options,
            'delay',
            required_type='bool',
            default=False
        )
        self.dry_run = Alerter.get_config_option(
            config_options,
            'dry_run',
            required_type='bool',
            default=False
        )
        self.ooh_recovery = Alerter.get_config_option(
            config_options,
            'ooh_recovery',
            required_type='bool',
            default=False
        )

        if Alerter.get_config_option(
            config_options,
            'debug_times',
            required_type=bool,
            default=False
        ):
            self.time_info = [
                (datetime.datetime.utcnow() - datetime.timedelta(minutes=1)).time(),
                (datetime.datetime.utcnow() + datetime.timedelta(minutes=1)).time()
            ]
            self.alerter_logger.debug("set times for alerter to %s", self.time_info)

    @staticmethod
    def get_config_option(config_options, key, **kwargs):
        kwargs['exception'] = AlerterConfigurationError
        return get_config_option(config_options, key, **kwargs)

    def set_dependencies(self, dependency_list):
        """Record which monitors we depend on.
        If a monitor we depend on fails, it means we can't reach the database, so we shouldn't bother trying to write to it."""

        self.dependencies = dependency_list

    def set_groups(self, group_list):
        """Record which groups we alert"""

        self.groups = group_list

    def check_dependencies(self, failed_list):
        """Check if anything we depend on has failed."""
        for dependency in failed_list:
            if dependency in self.dependencies:
                self.available = False
                return False
        self.available = True

    def should_alert(self, monitor):
        """Check if we should bother alerting, and what type."""
        out_of_hours = False

        if not self.available:
            return ""

        if not self.allowed_today():
            out_of_hours = True

        if not self.allowed_time():
            out_of_hours = True

        if monitor.virtual_fail_count() > 0:
            self.alerter_logger.debug("monitor %s has failed", monitor.name)
            # Monitor has failed (not just first time)
            if self.delay_notification:
                if not out_of_hours:
                    if monitor.name in self.ooh_failures:
                        try:
                            self.ooh_failures.remove(monitor.name)
                        except Exception:
                            self.alerter_logger.warning("couldn't remove %s from OOH list; will maybe generate too many alerts.", monitor.name)
                        if self.support_catchup:
                            return "catchup"
                        return "failure"
            if monitor.virtual_fail_count() == self.limit or (self.repeat and (monitor.virtual_fail_count() % self.limit == 0)):
                # This is the first time or nth time we've failed
                if out_of_hours:
                    if monitor.name not in self.ooh_failures:
                        self.ooh_failures.append(monitor.name)
                        return ""
                return "failure"
            return ""
        elif monitor.all_better_now() and monitor.last_virtual_fail_count() >= self.limit:
            try:
                self.ooh_failures.remove(monitor.name)
            except Exception:
                pass
            if out_of_hours:
                if self.ooh_recovery:
                    return "success"
                else:
                    return ""
            return "success"
        else:
            return ""

    def send_alert(self, name, monitor):
        """Abstract function to do the alerting."""
        raise NotImplementedError

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

    def allowed_today(self):
        """Check if today is an allowed day for an alert."""
        if datetime.datetime.now().weekday() not in self.days:
            return False
        return True

    def allowed_time(self):
        """Check if now is an allowed time for an alert."""
        if self.times_type == "always":
            return True
        now = datetime.datetime.now().time()
        if self.times_type == "only":
            if (now > self.time_info[0]) and (now < self.time_info[1]):
                return True
            else:
                return False
        elif self.times_type == "not":
            if (now > self.time_info[0]) and (now < self.time_info[1]):
                return False
            else:
                return True
        else:
            self.alerter_logger.error("this should never happen! Unknown times_type in alerter")
            return True
