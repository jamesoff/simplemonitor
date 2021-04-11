logfile - write a logfile
^^^^^^^^^^^^^^^^^^^^^^^^^

Writes a log file of the status of monitors.

The logfile format is::

    datetime monitor-name: status; VFC=vfc (message) (execution-time)

where the fields have the following meanings:

datetime
    the datetime of the entry. Format is controlled by the ``dateformat`` configuration option.

monitor-name
    the name of the monitor

status
    either ``ok`` if the monitor succeeded, or ``failed since YYYY-MM-DD HH:MM:SS``

vfc
    the virtual failure count: the number of failures of the monitor beyond its :ref:`tolerance<monitor-tolerance>`. Not present for **ok** lines.

message
    the message the monitor recorded as the reason for failure. Not present for **ok** lines.

execution-time
    the time the monitor took to execute its check


.. confval:: filename

    :type: string
    :required: true

    the filename to write to. Rotating this file underneath SimpleMonitor will likely result to breakage. See https://github.com/jamesoff/simplemonitor/issues/620.

.. confval:: buffered

    :type: boolean
    :required: false
    :default: true

    disable to use unbuffered writes to the logfile, allowing it to be watched in real time. Otherwise, you will find that updates don't appear in the file immediately.

.. confval:: only_failures

    :type: boolean
    :required: false
    :default: false

    set to have only monitor failures written to the log file (almost, but not quite, turning it into an alerter)

.. confval:: dateformat

    :type: string
    :required: false
    :default: ``timestamp``

    the date format to write for log lines. (Note that the timezone is controlled by the :ref:`tz<logger-tz>` configuration value.) Accepted values are:

    * ``timestamp`` (UNIX timestamp)
    * ``iso8601`` (``YYYY-MM-DDTHH:MM:SS``)
