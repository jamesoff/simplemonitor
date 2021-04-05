.. SimpleMonitor documentation master file, created by
   sphinx-quickstart on Sun Jan 31 19:23:11 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to SimpleMonitor
========================

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Getting started

   installation
   configuration

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Configuration Reference

   monitors
   alerters
   loggers
   configuration-examples

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Extending

   creating-monitors
   creating-alerters
   creating-loggers


SimpleMonitor is a Python script which monitors hosts and network
connectivity. It is designed to be quick and easy to set up and lacks complex
features that can make things like Nagios, OpenNMS and Zenoss overkill for a
small business or home network. Remote monitor instances can send their
results back to a central location.

SimpleMonitor supports Python 3.6.2 and higher on Windows, Linux and FreeBSD.

Features
========

Things SimpleMonitor can monitor
--------------------------------

For the complete list, see :ref:`Monitors<monitors-list>`.

* Host ping
* Host open ports (TCP)
* HTTP (is a URL fetchable without error? Does the page content it match a regular expression?)
* DNS record return value
* Services: Windows, Linux, FreeBSD services are supported
* Disk space
* File existence, age and time
* FreeBSD portaudit (and pkg audit) for security notifications
* Load average
* Process existence
* Exim queue size monitoring
* APC UPS monitoring (requires apcupsd to be installed and configured)
* Running an arbitrary command and checking the output
* Compound monitors to combine any other types

Adding your own Monitor type is straightforward with a bit of Python knowledge.

Logging and Alerting
--------------------

To SimpleMonitor, a Logger is something which reports the status of every
monitor, each time it's checked. An Alerter sends a message about a monitor
changing state.

Some of the options include (for the complete list, see :ref:`Loggers<loggers-list>` and :ref:`Alerters<alerters-list>`):

* Writing the state of each monitor at each iteration to a SQLite database
* Sending an email alert when a monitor fails, and when it recovers, directly over SMTP or via Amazon SES
* Writing a log file of all successes and failures, or just failures
* Sending a message via BulkSMS, Amazon Simple Notification Service (SNS), Telegram, Slack, MQTT (with HomeBridge support) and more
* Writing an HTML status page
* Writing an entry to the syslog (non-Windows only)
* Executing arbitary commands on monitor failure and recovery

Other features
--------------

* Simple configuration file format: it’s a standard INI file for the overall configuration and another for the monitor definitions
* Remote monitors: An instance running on a remote machine can send its results back to a central instance for central logging and alerting
* Dependencies: Monitors can be declared as depending on the success of others. If a monitor fails, its dependencies will be skipped until it succeeds
* Tolerance: Monitors checking things the other side of unreliable links or which have many transient failures can be configured to require their test to fail a number of times in a row before they report a problem
* Escalation of alerts: Alerters can be configured to require a monitor to fail a number of times in a row (after its tolerance limit) before they fire, so alerts can be sent to additional addresses or people
* Urgency: Monitors can be defined as non-urgent so that urgent alerting methods (like SMS) are not wasted on them
* Per-host monitors: Define a monitor which should only run on a particular host and all other hosts will ignore it – so you can share one configuration file between all your hosts
* Groups: Configure some Alerters to only react to some monitors
* Monitor gaps: By default every monitor polls every interval (e.g. 60 seconds). Monitors can be given a gap between polls so that they only poll once a day (for example)
* Alert periods: Alerters can be configured to only alert during certain times and/or on certain days
* Alert catchup: ...and also to alert you to a monitor which failed when they were unable to tell you. (For example, I don’t want to be woken up overnight by an SMS, but if something’s still broken I’d like an SMS at 7am as I’m getting up.)

Contributing
============

* Clone the GitHub repo
* ``poetry install``

You can use ``pre-commit`` to ensure your code is up to my exacting standards ;)

You can run tests with ``make unit-test``. See the Makefile for other useful targets.

Licence
=======

SimpleMonitor is released under the BSD Licence.

Contact
=======

* Open an issue or start a discussion on `GitHub <https://github.com/jamesoff/simplemonitor>`_
* Twitter: `@jamesoff <https://twitter.com/jamesoff>`_
* Email: james at jamesoff dot net

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
