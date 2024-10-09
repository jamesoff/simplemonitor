Monitor Configuration
=====================

Monitors are defined in (by default) :file:`monitors.ini`. The monitor is named
by its ``[section]`` heading. If you create a ``[defaults]`` section, the
values are used as defaults for all the other monitors. Each monitor's
configuration will override the values from the default.

.. contents::


Common options
--------------

These options are common to all monitor types.

.. confval:: type

   :type: string
   :required: true

    the type of the monitor; one of those in the list below.

.. confval:: runon

   :type: string
   :required: false
   :default: none

    a hostname on which the monitor should run. If not set, always runs. You
    can use this to share one config file among many hosts. (The value which is
    compared to is that returned by Python's :code:`socket.gethostname()`.)

.. confval:: depend

   :type: comma-separated list of string
   :required: false
   :default: none

   the monitors on which this one depends. This monitor will run after those, unless one of them fails or is skipped, in which case this one will also skip. A skip does not trigger an alerter.

.. _monitor-tolerance:

.. confval:: tolerance

    :type: integer
    :required: false
    :default: 1

    the number of times a monitor can fail before it enters the failed state. Handy for things which intermittently fail, such as unreliable links. The number of times the monitor has actually failed, minus this number, is its "Virtual Failure Count". See also the :ref:`limit<alerter-limit>` option on Alerters.

.. confval:: urgent

    :type: boolean
    :required: false
    :default: true

    if this monitor is "urgent" or not. Non-urgent monitors do not trigger urgent alerters (e.g. BulkSMS)

.. _gap:

.. confval:: gap

    :type: integer
    :required: false
    :default: 0

    the number of seconds this monitor should allow to pass before polling. Use it to make a monitor poll only once an hour (``3600``), for example. Setting this value lower than the ``interval`` will have no effect, and the monitor will run every loop like normal.

    Some monitors default to a higher value when it doesn't make sense to run their check too frequently because the underlying data will not change that often or quickly, such as :ref:`pkgaudit<pkgaudit>`. You can override their default to a lower value as required.

    .. hint:: Monitors which are in the failed state will poll every loop, regardless of this setting, in order to detect recovery as quickly as possible

.. _monitor-remote-alert:

.. confval:: remote_alert

    :type: boolean
    :required: false
    :default: false

    set to true to have this monitor's alerting handled by a remote instance instead of the local one. If you're using the remote feature, this is a good candidate to put in the ``[defaults]``.

.. confval:: recover_command

    :type: string
    :required: false
    :default: none

    a command to execute once when this monitor enters the failed state. For example, it could attempt to restart a service.

.. confval:: recovered_command

    :type: string
    :required: false
    :default: none

    a command to execute once when this monitor returns to the OK state. For example, it could restart a service which was affected by the failure of what this monitor checks.

.. confval:: notify

    :type: boolean
    :required: false
    :default: true

    if this monitor should alert at all.

.. _monitor-group:

.. confval:: group

    :type: comma-separated list of string
    :required: false
    :default: ``default``

    the group(s) the monitor belongs to. Alerters and Loggers will only fire for monitors which appear in their groups.

.. confval:: failure_doc

    :type: string
    :required: false
    :default: none

    information to include in alerts on failure (e.g. a URL to a runbook)

.. _monitor-gps:

.. confval:: gps

    :type: string
    :required: no, unless you want to use the :ref:`html logger<logger-html>`'s map

    comma-separated latitude and longitude of this monitor

.. confval:: enabled

    :type: boolean
    :required: false
    :default: true

    Set to false to turn off the monitor


.. _monitors-list:

Monitors
--------

.. note:: The ``type`` of the monitor is the first word in its heading.

.. toctree::
   :glob:

   monitors/*
