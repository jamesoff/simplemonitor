Alerter Configuration
=====================

Alerters send one-off alerts when a monitor fails. They can also send an alert
when it succeeds again.

An alerter knows if it is urgent or not; if a monitor defined as non-urgent
fails, an urgent alerter will not trigger for it. This means you can avoid
receiving SMS alerts for things which don’t require your immediate attention.

Alerters can also have a time configuration for hours when they are or are not
allowed to alert. They can also send an alert at the end of the silence period
for any monitors which are currently failed.

Alerters are defined in the main configuration file, which by default is :file:`monitor.ini`. The section name is the name of your alerter, which you should then add to the ``alerters`` configuration value.

.. contents::

Common options
--------------

These options are common to all alerter types.

.. confval:: type

    :type: string
    :required: true

    the type of the alerter; one of those in the list below.

.. confval:: depend

    :type: comma-separated list of string
    :required: false
    :default: none

    a list of monitors this alerter depends on. If any of them fail, no attempt will be made to send the alert.

.. _alerter-limit:

.. confval:: limit

    :type: integer
    :required: false
    :default: ``1``

    the (virtual) number of times a monitor must have failed before this alerter fires for it. You can use this to escalate an alert to another email address or text messaging, for example. See the :ref:`tolerance<monitor-tolerance>` Monitor configuration option.

.. confval:: dry_run

    :type: boolean
    :required: false
    :default: ``false``

    makes an alerter do everything except actually send the message, and instead will print some information about what it would do.

.. confval:: ooh_success

    :type: boolean
    :required: false
    :default: ``false``

    makes an alerter trigger its success action even if out of hours

.. confval:: groups

    :type: comma-separated list of string
    :required: false
    :default: ``default``

    list of monitor groups this alerter should fire for. See the :ref:`group<monitor-group>` setting for monitors.

.. confval:: only_failures

    :type: boolean
    :required: false
    :default: ``false``

    if true, only send alerts for failures (or catchups)

.. _alerter-tz:

.. confval:: tz

    :type: string
    :required: false
    :default: ``UTC``

    the timezone to use in alert messages. See also :confval:`times_tz`.

.. confval:: repeat

    :type: boolean
    :required: false
    :default: ``false``

    fire this alerter (for a failed monitor) every iteration

.. confval:: urgent

    :type: boolean
    :required: false

    if the alerter should be urgent or not. The default varies from alerter to
    alerter. Typically, those which send "page" style alerts such as SMS default
    to urgent. You can use this option to override that in e.g. the case of the
    SNS alerter, which could be urgent if sending SMSes, but non-urgent if
    sending emails.

Time restrictions
-----------------

All alerters accept time period configuration. By default, an alerter is active at all times, so you will always immediately receive an alert at the point where a monitor has failed enough (more times than the limit). To set limits on when an alerter can send, use the configuration values below.

Note that the :confval:`times_type` option sets the timezone all the values are interpreted as. The default is the local timezone of the host evaluating the logic.

.. confval:: day

    :type: comma-separated list of integer
    :required: false
    :default: all days

    which days an alerter can operate on. ``0`` is Monday, ``6`` is Sunday.

.. confval:: times_type

    :type: string
    :required: false
    :default: ``always``

    one of ``always``, ``only``, or ``not``. ``only`` means that the limits specify the period the alerter is allowed to operate in. ``not`` means the specify the period it isn't, and outside of that time it is allowed.

.. confval:: time_lower

    :type: string
    :required: when :confval:`times_type` is not ``always``

    the lower end of the time range. Must be lower than :confval:`time_upper`. The format is ``HH:mm`` in 24-hour clock.

.. confval:: time_upper

    :type: string
    :required: when :confval:`times_type` is not ``always``

    the upper end of the time range. Must be lower than :confval:`time_lower`. The format is ``HH:mm`` in 24-hour clock.

.. confval:: times_tz

    :type: string
    :required: false
    :default: the host's local time

    the timezone for :confval:`day`, :confval:`time_lower` and :confval:`time_upper` to be interpreted in.

.. confval:: delay

    :type: boolean
    :required: false
    :default: ``false``

    set to true to have the alerter send a "catch-up" alert about a failed monitor if it failed during a time the alerter was not allowed to send, and is still failed as the alerter enters the time it is allowed to send. If the monitor fails and recovers during the not-allowed time, no alert is sent either way.


Time examples
^^^^^^^^^^^^^

These snippets omit the alerter-specific configuration values.

Don't trigger during the hours I'm in the office (8:30am to 5:30pm, Monday to Friday):

.. code-block:: ini

   [out_of_hours]
   type=some-alerter-type
   times_type=not
   time_lower=08:30
   time_upper_17:30
   days=0,1,2,3,4

Don't send at antisocial times, but let me know later if something broke and hasn't recovered yet:

.. code-block:: ini

   [polite_alerter]
   type=some-alerter-type
   times_type=only
   time_lower=07:30
   time_upper=22:00
   delay=1

.. _alerters-list:

Alerters
--------

.. note:: The ``type`` of the alerter is the first word in its heading.

.. toctree::
   :glob:

   alerters/*
