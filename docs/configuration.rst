-------------
Configuration
-------------

The main configuration lives in :file:`monitor.ini` in the same directory as the code.

Section names are lowercase in square brackets. Settings are defined as key=value. Lines can be commented with ``#``.

Monitor section
---------------

interval
  defines how many seconds to wait between running all the monitors. Note that the time taken to run the monitors is not subtracted from the interval, so the next iteration will run at `interval + time_to_run_monitors` seconds. Required. 

monitors
  defines the filename to load the monitors themselves from. Optional; default = :file:`monitors.ini`

pidfile
  gives a path to write a pidfile in. Optional.

remote
  enables the listener for receiving data from remote instances. Set to 1 to enable. Optional; default = 0

remote_port
  gives the TCP port to listen on for data. Required if `remote` is enabled. No default.

key
  shared secret for validating data from remote instances. Required if `remote` is enabled. No default.

Reporting section
-----------------

loggers
  lists (comma-separated, no spaces) the names of the loggers you have defined. (You can define loggers and not add them to this setting.) Not required; no default.

alerters
  lists the names of the alerters you have defined. Not required; no default.

If you do not define any loggers or alerters, then the only way to monitor the status of your network will be to watch the window the script is running in!

* [Configuring logging](logging.html)
* [Configuring alerting](alerting.html)

Monitors
--------

Monitors go in :file:`monitors.ini` (or another file, if you changed the *monitors* setting above). [1]_

Let’s have a look at an example configuration with inline notes.

Here's :file:`monitor.ini`:

.. code:: ini

  [monitor]
  # poll every minute
  interval=60

  [reporting]
  # define one reporter
  loggers=logfile
  # and three alerters
  alerters=email,email_escalate,sms

  # the rest of the file is sections named for the reporters and loggers

  [logfile]
  # write a logfile called monitor.log, with only the failures recorded
  type=logfile
  filename=monitor.log
  only_failures=1

  [email]
  # send me an email via mailserver.domain.local
  type=email
  host=mailserver.domain.local
  from=monitor@domain.local
  to=administrator@domain.local

  [email_escalate]
  # send my boss an email after a monitor has failed 5 times in a row
  type=email
  host=mailserver.domain.local
  from=monitor@domain.local
  to=boss@domain.local
  limit=5

  [sms]
  # send an SMS after a monitor has failed 10 times in a row
  type=bulksms
  username=some_username
  password=some_password
  target=some_mobile_number
  limit=10


Now we need to write our :file:`monitors.ini`:

.. code:: ini

    # here we just list our monitors, which are named by their section

    [london-ping]
    # ping this host, and allow it two failures in a row before we consider it
    # failed
    type=host
    host=london-vpn-endpoint.domain.local
    tolerance=2

    [london-server]
    # ping this host, and allow it two failures as above. also, since it's at
    # the other end of the VPN, if the monitor above fails, we will skip this
    # one
    type=host
    host=london-server.domain.local
    tolerance=2
    depend=london-ping

    [website-http]
    # monitor a website, but only check it every 5 minutes. Don't trigger
    # urgent alerters (e.g. SMS) on failure
    type=http
    url=http://www.domain.local
    urgent=0
    gap=300

    [webmail-http]
    # monitor our webmail server, which we expect to ask us to authenticate
    type=http
    url=http://webmail.domain.local
    allowed_codes=401

    [local-diskspace]
    # make sure this partition has 500MB free
    type=diskspace
    partition=/spool
    limit=500M

    [local-exim]
    # make sure exim is running. this monitor only executes on
    # mailserver.domain.local
    type=rc
    runon=mailserver.domain.local
    service=exim

    [local-smtp]
    # make sure exchange is running. this monitor only executes on
    # exchange.domain.local
    type=service
    runon=exchange.domain.local
    service=smtpsvc

This example configuration contains several combinations of monitors you probably won’t use on the same server – particularly a diskspace check for a mounted partition (not a drive letter) and a Windows service monitor. I just put them all together here as an example :)

.. rubric:: Footnotes

.. [1] Yes, I know the two filenames are poor choices, I'm sorry
