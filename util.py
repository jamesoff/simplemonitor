"""Utilities for SimpleMonitor."""

import datetime


class MonitorConfigurationError(ValueError):
    """A config error for a Monitor"""
    pass


class AlerterConfigurationError(ValueError):
    """A config error for an Alerter"""
    pass


class LoggerConfigurationError(ValueError):
    """A config error for a Logger"""
    pass


def get_config_option(config_options, key, **kwargs):
    """Get a value out of a dict, with possible default, required type and requiredness."""
    exception = kwargs.get('exception', ValueError)

    if not isinstance(config_options, dict):
        raise exception('config_options should be a dict')

    default = kwargs.get('default', None)
    required = kwargs.get('required', False)
    value = config_options.get(key, default)
    if required and value is None:
        raise exception('config option {0} is missing and is required'.format(key))
    required_type = kwargs.get('required_type', 'str')
    allowed_values = kwargs.get('allowed_values', None)
    allow_empty = kwargs.get('allow_empty', True)
    if isinstance(value, str) and required_type:
        if required_type == 'str' and value == '' and not allow_empty:
            raise exception('config option {0} cannot be empty'.format(key))
        if required_type in ['int', 'float']:
            try:
                if required_type == 'int':
                    value = int(value)
                else:
                    value = float(value)
            except ValueError:
                raise exception('config option {0} needs to be an {1}'.format(key, required_type))
            minimum = kwargs.get('minimum')
            if minimum is not None and value < minimum:
                raise exception('config option {0} needs to be >= {1}'.format(key, minimum))
            maximum = kwargs.get('maximum')
            if maximum is not None and value > maximum:
                raise exception('config option {0} needs to be <= {1}'.format(key, maximum))
        if required_type == '[int]':
            try:
                value = [int(x) for x in value.split(",")]
            except ValueError:
                raise exception('config option {0} needs to be a list of int[int,...]'.format(key))
        if required_type == 'bool':
            value = bool(value.lower() in ['1', 'true', 'yes'])
        if required_type == '[str]':
            value = [x.strip() for x in value.split(",")]
    if isinstance(value, list) and allowed_values:
        if not all([x in allowed_values for x in value]):
            raise exception('config option {0} needs to be one of {1}'.format(key, allowed_values))
    else:
        if allowed_values is not None and value not in allowed_values:
            raise exception('config option {0} needs to be one of {1}'.format(key, allowed_values))
    return value


def format_datetime(the_datetime):
    """Return an isoformat()-like datetime without the microseconds."""
    if the_datetime is None:
        return ""

    if isinstance(the_datetime, datetime.datetime):
        the_datetime = the_datetime.replace(microsecond=0)
        return the_datetime.isoformat(' ')
    return the_datetime
