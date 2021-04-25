.. _logger-logfileng:

logfileng - write a logfile with rotation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Writes a log file of the status of monitors. Rotates and deletes old log files based on size or age.

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

    the filename to write to. Rotated logs have either ``.N`` (where N is an incrementing number) or the date/time appended to the filename, depending on the rotation mode.

.. confval:: rotation_type

    :type: string
    :required: true

    one of ``time`` or ``size``

.. confval:: when

    :type: string
    :required: false
    :default: ``h``

    Only for rotation based on time. The units represented by ``interval``. One of ``s`` for seconds, ``m`` for minutes, ``h`` for hours, or ``d`` for days

.. confval:: interval

    :type: integer
    :required: false
    :default: ``1``

    Only for rotation based on time. The number of ``when`` between file rotations.

.. confval:: max_bytes

    :type: :ref:`bytes<config-bytes>`
    :required: yes, when rotation_type is ``size``

    the maximum log file size before it is rotated.

.. confval:: backup_count

    :type: integer
    :required: false
    :default: ``1``

    the number of old files to keep

.. confval:: only_failures

    :type: boolean
    :required: false
    :default: false

    set to have only monitor failures written to the log file (almost, but not quite, turning it into an alerter)
