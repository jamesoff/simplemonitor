---
layout: page
title: Configuring SimpleMonitor
order: 20
---

The main configuration lives in monitor.ini in the same directory as the code.

Section names are lowercase in square brackets. Settings are defined as key=value. Lines can be commented with #.

## Monitor section

| setting | description | required | default |
|---|---|---|---|
| interval | defines how many seconds to wait between running all the monitors. Note that the time taken to run the monitors is not subtracted from the interval, so the next iteration will run at `interval + time_to_run_monitors` seconds. | yes | |
| monitors | defines the filename to load the monitors themselves from. | no | `monitors.ini`
| pidfile | gives a path to write a pidfile in. | no | |
| remote | enables the listener for receiving data from remote instances. Set to 1 to enable. | no | 0 |
| remote_port | gives the TCP port to listen on for data. | if `remote` is enabled | |
| key | shared secret for validating data from remote instances. | if `remote` is enabled | |

## Reporting section
*loggers* lists (comma-separated, no spaces) the names of the loggers you have defined. (You can define loggers and not add them to this setting.) Not required; no default.

*alerters* lists the names of the alerters you have defined. Not required; no default.

If you do not define any loggers or alerters, then the only way to monitor the status of your network will be to watch the window the script is running in!

* [Configuring logging](logging.html)
* [Configuring alerting](alerting.html)

## Monitors
Monitors go in monitors.ini (or another file, if you changed the *monitors* setting above).

Let’s have a look at an example configuration.

Here’s monitor.ini:
{% highlight ini %}
[monitor]
interval=60

[reporting]
loggers=logfile
alerters=email,email_escalate,sms

[logfile]
type=logfile
filename=monitor.log
only_failures=1

[email]
type=email
host=mailserver.domain.local
from=monitor@domain.local
to=administrator@domain.local

[email_escalate]
type=email
host=mailserver.domain.local
from=monitor@domain.local
to=boss@domain.local
limit=5

[sms]
type=bulksms
username=some_username
password=some_password
target=some_mobile_number
limit=10
{% endhighlight %}

What does this configuration do? Firstly, it only polls every minute. It has one logger, writing a logfile, and three alerters – two emails and one SMS.

The logfile is written to monitor.log and only contains failures.

An email is sent to administrator@domain.local when a monitor fails. After a monitor has failed another four times, an email is sent to my boss. After it’s failed another five times (for a total of ten), I get an SMS.

Now we need to write our monitors.ini:
{% highlight ini %}
[london-ping]
type=host
host=london-vpn-endpoint.domain.local
tolerance=2

[london-server]
type=host
host=london-server.domain.local
tolerance=2
depend=london-ping

[website-http]
type=http
url=http://www.domain.local
urgent=0
gap=300

[webmail-http]
type=http
url=http://webmail.domain.local
allowed_codes=401

[local-diskspace]
type=diskspace
partition=/spool
limit=500M

[local-exim]
type=rc
runon=mailserver.domain.local
service=exim

[local-smtp]
type=service
runon=exchange.domain.local
service=smtpsvc
{% endhighlight %}

This is what it all means:

* A monitor called london-ping pings the endpoint of our VPN to the London office. This sometimes gets lost in transit even if the link is up, so the tolerance for this monitor is 2.
* We also ping london-server. As it’s the other end of the VPN, we also give it a tolerance of 2. We declare that it depends on london-ping, so if the VPN is down we don’t get additional alerts for london-server.
* Next we use an HTTP monitor to check our website is working. I don’t need to be SMSed if it breaks, so we set it as not urgent. Also, we’ll only check it every 5 minutes (300 seconds).
* We want to check our webmail interface is responding, but it needs authentication. We’ll allow the HTTP error 401 Authentication Required to count as success.
* We need to make sure the /spool partition on this server always has at least 500MB of free space.
* We also want to make sure that exim is running on our FreeBSD server mailserver.domain.local. This monitor won’t try to run anywhere else.
* Finally, we want to check the SMTP service is running on our Exchange server.

This example configuration contains several combinations of monitors you probably won’t use on the same server – particularly a diskspace check for a mounted partition (not a drive letter) and a Windows service monitor. I just put them all together here as an example :)
