---
layout: page
title: Alerting
order: 40
---

Alerters send one-off alerts when a monitor fails. They can also send an alert when it succeeds again.

An alerter knows if it is urgent or not; if a monitor defined as non-urgent fails, an urgent alerter will not trigger for it. This means you can avoid receiving SMS alerts for things which don’t require your immediate attention.

The types of alerter are:

* email: Sends an email when a monitor fails. Sends an email when it succeeds again. Requires an SMTP server to talk to. Non-urgent (all monitors will trigger this alerter.)
* bulksms: Sends an SMS alert when a monitor fails. Does not send an alert for when it succeeds again. Uses the [BulkSMS](http://www.bulksms.co.uk) service, which requires subscription. The messages are sent over HTTP on port 5567. (Urgent, so urgent=0 monitors will not trigger an SMS.)
* syslog: Writes an entry to the syslog when something fails or succeeds. Not supported on Windows.
* execute: Executes an arbitary command when something fails or recovers.

## Defining an alerter
The section name should be the name of your alerter. This is the name you should give in the “alerters” setting in the reporting section of the main configuration. All alerters share these settings:

| setting | description | required | default |
|---|---|---|---|
|type|the type of the alerter, from the list above|yes| |
|depend|a list of monitors this alerter depends on. If any of them fail, no attempt will be made to send the alert. (For example, there’s no point trying to send an email alert to an external address if your route(s) to the Internet are down.)|no| |
|limit|the number of times a monitor must fail before this alerter will fire. You can use this to escalate an alert to another email address if the problem is ongoing for too long, for example.|no|1|
|dry_run|makes an alerter do everything except actually send the message. Instead it will print some information about what it would do. Use when you want to test your configuration without generating emails/SMSes. Set to 1 to enable.|no|0|
|ooh_success|makes an alerter trigger its success action even if out-of-hours (0 or 1)|no|0|

The *limit* uses the virtual fail count of a monitor, which means if a monitor has a tolerance of 3 and the alerter has a limit of 2, the monitor must fail 5 times before an alert is sent.

## Time periods
All alerters accept time period configuration. By default, an alerter is active at all times, so you will always immediately receive an alert at the point where a monitor has failed enough (more times than the *limit*). To set limits on when an alerter can send:

| setting | description | required | default |
|---|---|---|---|
|day|Which days an alerter can operate on. This is a comma-separated list of integers. 0 is Monday and 6 is Sunday.|no|(all days)|
|times_type|Set to one of always, only, or not. “Only” means that the limits define the period that an alerter can operate. “Not” means that the limits define the period during which it will not operate.|no|always|
|time_lower and time_upper| If *times_type* is only or not, these two settings define the time limits. time_lower must always be the lower time. The time format is hh:mm using 24-hour clock. Both are required if times_type is anything other than always.|when *times_type* is not `always`| |
|delay|If any kind of time/day restriction applies, the alerter will notify you of any monitors that failed while they were unable to alert you and are still failed. If a monitor fails and recovers during the restricted period, no catch-up alert is generated. Set to 1 to enable.|no|0|

Here’s a quick example of setting time periods (some other configuration values omitted):

Don’t send me SMSes while I’m in the office (8:30am to 5:30pm Mon-Fri):
{% highlight ini %}
[out_of_hours]
type=bulksms
times_type=not
time_lower=08:30
time_upper=17:30
days=0,1,2,3,4
{% endhighlight %}

Don’t send me SMSes at antisocial times, but let me know later if anything broke and didn’t recover:

{% highlight ini %}
[nice_alerter]
type=bulksms
times_type=only
time_lower=07:30
time_upper=22:00
delay=1
{% endhighlight %}

## Email alerters

| setting | description | required | default |
|---|---|---|---|
|host|the email server to send the message to (via SMTP).|yes| |
|from|the email address the email should come from.|yes| |
|to|the email address to email should go to.|yes| |

## BulkSMS alerters

| setting | description | required | default |
|---|---|---|---|
|sender|who the SMS should appear to be from. Max 11 chars. Try to avoid non alphanumeric characters.|no|SmplMntr|
|username|your BulkSMS username.|yes| |
|password|your BulkSMS password.|yes| |
|target|the number to send the SMS to. Prefix the country code but drop the +. UK example: 447777123456.|yes| |

## Syslog alerters
Syslog alerters have no additional options.

## Execute alerters

| setting | description | required | default |
|---|---|---|---|
|fail_command|The command to execute when a monitor fails.|no| |
|success_command|The command to execute when a monitor recovered.|no| |
|catchup_command|THe command to execute when a previously-failed but not-alerted monitor enters a time period when it can alert. See the `delay` option above.|no| |

You can use the string `fail_command` for catchup_command to make it use the value of fail_command.

The following variables will be replaced in the string when the command is executed:

* hostname: the host the monitor is running on
* name: the monitor's name
* days, hours, minutes, seconds: the monitor's downtime
* failed_at: the date and time the monitor failed at
* virtual_fail_count: the virtual fail count of the monitor
* info: the additional information the monitor recorded about its status
* description: a description of what the monitor is checking for

You may need to quote parameters - e.g. `fail_command=say "Oh no, monitor {name} has failed at {failed_at}"`
