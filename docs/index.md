---
layout: page
title: SimpleMonitor
show_downloads: true
order: 10
---

SimpleMonitor is a Python script which monitors hosts and network connectivity. It is designed to be quick and easy to set up and lacks complex features that can make things like Nagios, OpenNMS and Zenoss overkill for a small business or home network. Remote monitor instances can send their results back to a central location.

### SimpleMonitor supports:

* Ping monitoring (is a host pingable?)
* TCP monitoring (is a host listening on a TCP port?)
* HTTP monitoring (is a URL fetchable without error? Optionally, does the page content it match a regular expression?)
* DNS record monitoring
* Service monitoring: FreeBSD 'rc' (and potenially others), Windows services, daemontools service
* Disk space monitoring
* File existence, age and time
* FreeBSD portaudit (and pkg audit)
* Load average monitoring
* Exim queue size monitoring
* Windows DHCP scope (available IPs)
* APC UPS monitoring (requires apcupsd to be installed and configured)
* Running an arbitary command and checking the output
* A monitor which is a compound of a number of the above

Adding more monitor types is quite simple if you are able to code in Python.

### Logging and alerting options are:

* Writing the state of each monitor at each iteration to a SQLite database (i.e. a history of results)
* Maintaining a snapshot of the current state of the monitors in a SQLite database
* Sending an email alert when a monitor fails, and when it recovers, directly over SMTP or via Amazon SES
* Writing a log file of all successes and failures, or just failures
* Sending a text message via BulkSMS (subscription required)
* Writing an HTML status page
* Writing an entry to the syslog (non-Windows only)
* Posting notifications to Slack, 46elks, Notify My Android, Pushbullet, and Pushover
* Executing arbitary commands on monitor failure and recovery

Again, adding more logging/alerting methods is simply a case of writing some Python.

### SimpleMonitor also features:

* Simple configuration file format: it’s a standard INI file for the overall configuration and another for the monitor definitions
* Dependencies: Monitors can be declared as depending on the success of others. If a monitor fails, its dependencies will be skipped until it succeeds.
* Tolerance: Monitors checking things the other side of unreliable links or which have many transient failures can be configured to require their test to fail a number of times in a row before they report a problem.
* Escalation of alerts: Alerters can be configured to require a monitor to fail a number of times in a row (after its tolerance limit) before they fire, so alerts can be sent to additional addresses or people.
* Urgency: Monitors can be defined as non-urgent so that urgent alerting methods (like SMS) are not wasted on them.
* Per-host monitors: Define a monitor which should only run on a particular host and all other hosts will ignore it – so you can share one configuration file between all your hosts.
* Monitor gaps: By default every monitor polls every interval (e.g. 60 seconds). Monitors can be given a gap between polls so that they only poll once a day (for example).
* Alert periods: Alerters can be configured to only alert during certain times and/or on certain days…
* Alert catchup: …and also to alert you to a monitor which failed when they were unable to tell you. (For example, I don’t want to be woken up overnight by an SMS, but if something’s still broken I’d like an SMS at 7am as I’m getting up.)
* Remote monitors: An instance running on a remote machine can send its results back to a central instance for logging and alerting.

## Getting started

* Download the code
* Install dependencies: `pip install -r requirements.txt`
* Write your configuration files
* Run the code

## Running SimpleMonitor

* `python monitor.py`

That was easy.

For help on command line options, run `python monitor.py -h`, or see below.

SimpleMonitor does not fork.

On non-Windows, SimpleMonitor runs very nicely under daemontools. You just need a run file a bit like this:

{% highlight bash %}
#!/bin/sh

cd /usr/local/monitor && exec /usr/local/bin/python monitor.py -q
{% endhighlight %}

On Windows hosts, you’ll have to leave it running in a Command Prompt for now; I haven’t gotten round to making it run as a service.

In the `scripts` folder you can find startup scripts for various systems. You will need to adjust paths, usernames and options before using them!


## Command line options

* `-h`, `--help`: display help

### Configuration

* `-f CONFIG`, `--config=CONFIG`: configuration file (monitor.ini)
* `-p PIDFILE`, `--pidfile=PIDFILE`: Write PID into this file
* `-N`, `--no-network`: Disable network listening socket (if enabled in config)

### Testing

These options exist mainly for automated testing and validation.

* `-t`, `--test`: Test config and exit. Exits non-zero if config is broken
* `-1`, `--one-shot`: Run the monitors once only, without alerting. Require monitors without "fail" in the name to succeed. Require monitors with "skip" in the name to skip. Exit zero or non-zero accordingly.
* `--loops`: (Undocumented) Run this many loops of checks/logging/alerting and exit

### Output

SimpleMonitor currently outputs everything to stdout.

* `-v`, `--verbose`: Be more verbose
* `-q`, `--quiet`: Don't output anything except errors
* `-d`, `--debug`: Enable debug output (and enable verbose mode)
* `-H`, `--no-heartbeat`: Omit printing the '.' character when running checks

## Licence

SimpleMonitor is released under the BSD licence.
