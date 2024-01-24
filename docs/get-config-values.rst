.. _get-config-option-helper:

Getting configuration values
============================

When loading configuration values for Monitors, Alerters and Loggers, you can use the `get_config_option()` function to perform sanity checks on the loaded config.

.. py:function:: get_config_option(config_options: dict, key: str, [default=None[, required=False[, required_type="str"[, allowed_values=None[, allow_empty=True[, minimum=None[,maximum=None]]]]]]])

    Get a config value out of a dict, and perform basic validation on it.

    :param dict config_options: The dict to get the value from
    :param str key: The key to the value in the dict
    :param default: The default value to return if the key is not found
    :param bool required: Throw an exception if the value is not present (and default is None)
    :param str required_type: One of str, int, float, bool, [int] (list of int), [str] (list of str)
    :param allowed_values: A list of allowed values
    :param bool allow_empty: Allow the empty string when required_type is "str"
    :param minimum: The minimum allowed value for int and float
    :param maximum: The maximum allowed value for int and float
    :type minimum: integer, float or None
    :type maximum: integer, float or None
    :return: the fetched configuration value (or the default)

    Note that the return type of the function signature covers all supported types, so you should use :py:func:`typing.cast` to help mypy understand. Do not use :ref:`assert<python:assert>`.
