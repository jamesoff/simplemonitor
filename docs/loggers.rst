Logger Configuration
=====================

Loggers record the state of every monitor after each interval.

Loggers are defined in the main configuration file, which by default is :file:`monitor.ini`. The section name is the name of your logger, which you should then add to the ``loggers`` configuration value.

.. contents::

Common options
--------------

These options are common to all logger types.

.. confval:: type

    :type: string
    :required: true

    the type of the logger; one of those in the list below.

.. confval:: depend

    :type: comma-separated list of string
    :required: false
    :default: none

    a list of monitors this logger depends on. If any of them fail, no attempt will be made to log.

.. confval:: groups

    :type: comma-separated list of string
    :required: false
    :default: ``default``

    list of monitor groups this logger should record. Use the special value ``_all`` to match all groups. See the :ref:`group<monitor-group>` setting for monitors.

.. _logger-tz:

.. confval:: tz

    :type: string
    :required: false
    :default: ``UTC``

    the timezone to convert date/times to

.. confval:: dateformat

    :type: string
    :required: false
    :default: ``timestamp``

    the date format to write for log lines. (Note that the timezone is controlled by the :ref:`tz<logger-tz>` configuration value.) Accepted values are:

    * ``timestamp`` (UNIX timestamp)
    * ``iso8601`` (``YYYY-MM-DDTHH:MM:SS``)

.. _loggers-list:

Loggers
-------

.. note:: The ``type`` of the logger is the first word in its heading.

.. toctree::
   :glob:

   loggers/*
