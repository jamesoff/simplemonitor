Monitors
========

Monitors are defined in :file:`monitors.ini`, or the file declared in by the
``monitors`` setting in the main config file. This file is a standard INI-style
configuration. Each monitor is declared by a name in square brackets, followed
by a set of ``key=value`` settings. A special name ``default`` is reserved, and
settings from this are inherited by every monitor (but can be overridden).

The only required setting for each monitor is its ``type``. Common options are
shared by all monitor types, and then each type has its own specific settings,
some of which may be required.

Types
-----

The types of monitor available are:

host
  Pings a host (once per iteration) to see if it's up.
service
  Checks a Windows service to make sure it's running.
tcp
  Checks a TCP port is open. Doesn't care what happens after the connection is opened.
rc
  Checks a FreeBSD-style service is running, by running its rc script with the ``status`` parameter.
svc
  Checks a supervise service is running.
diskspace
  Checks the free space on a partition.
http
  Attempts to fetch a URL and makes sure the HTTP code is acceptable. Can also
  match the contents of the body against a regexp.
dns
  Attempts to resolve a DNS record and check the result.
apcupsd
  Check an APC UPS (via apcupsd) for power status.
pkgaudit
  Check FreeBSD packages for known vulnerabilities.
loadavg
  Check the load average on the host.
command
  Run a command and optionally verify the output. If the command exits non-zero, reports failure.
compound
  Combine (logical-and) multiple failures of other monitors for emergency escalation.


Common configuration
--------------------

All monitor types share the following configuration options:

``type``

  One of the types of monitor from the list above.

  *Required*: yes

``runon``

  A hostname on which this monitor should run. If set, and not equal to the
  value of ``socket.gethostname()`` then the monitor is ignored. This allows a
  config file to be shared with multiple hosts.

  *Required*: no
  
  *Default*: (blank; run on all hosts)

``depend``

  A comma-separated list of monitors on which this monitor depends. Those
  monitors will be checked before this one. If a dependency fails or marks
  itself skipped, this monitor will also skip.

  *Required*: no

  *Default*: (blank; no dependencies)

``tolerance``

  The number of times this monitor should fail before it actually reports as
  failed. (This is the source of 'virtual fail count'.) This allows monitors of
  unreliable or tempermental things to ignore short failures.

  *Required*: no

  *Default*: 1

``urgent``

  Set to 0 to mark a monitor as non-urgent. Non-urgent monitors cannot trigger
  urgent alerters.

  *Required*: no

  *Default*: 1

``gap``

  Number of seconds between checks of this monitor. If this value is more than
  the global interval, then the monitor is only checked if it has been more
  than this many seconds since the last check. If this value is less than the
  global interval, the monitor is checked each time. Use it for things like
  pkgaudit, which are best checked once or twice a day.

  If the monitor is failed, it is re-checked every time to see if it has
  recovered.

  *Required*: no

  *Default*: 0

``remote_alert``

  If set, this monitor will not trigger alerters on its own host, but will
  trigger alerters on the remote host.

  *Required*: no

  *Default*: 0

``recover_command``

  A command to execute on the failure of the monitor. Success or failure of the
  command does not affect the state of the monitor; if the command resolves the
  problem, then the next check will detect it.

  *Required*: no

  *Default*: none

Monitor configuration
---------------------

Host
~~~~

Ping a host. Succeeds if the host responds within 5 seconds.

*Platforms*: all

``host``

  The hostname to ping.

  *Required*: yes

``ping_ttl``

  The TTL value to use in the ping command.

  *Required*: no

  *Default*: 5

Service
~~~~~~~

Check a Windows service is in the desired state.

*Platforms*: Windows only

``service``

  The Windows service name to check. This can be found as the *Service name* on the *General* tab of the service properties.

  *Required*: yes

``state``

  The state the service should be in: RUNNING or STOPPED

  *Required*: no

  *Default*: RUNNING

``host``

  The host to check on. To check a remote service, the user SimpleMonitor is running as will need suitable privileges across the network.

  *Required*: no

tcp
~~~

Checks a TCP port is open. Doesn't care what happens after the connection is opened, only that it can be.

*Platforms*: all

``host``

  The host to check.

  *Required*: yes

``port``

  The port number to check.

  *Required*: yes

rc
~~

Check a (typically) FreeBSD-style service is running, by running its rc script with the ``status`` command.

*Platforms*: FreeBSD; maybe Linux

``service``

  The service name to check i.e. the name of the rc.d script in ``/usr/local/etc/rc.d`` or ``/etc/rc.d``. Trailing ``.sh`` is not required.

  *Required*: yes

``path``

  The path containing the service script. Set to ``/etc/rc.d`` to monitor base services.

  *Required*: no

  *Default*: /usr/local/etc/rc.d

``return_code``

  The return code expected of the script.

  *Required*: no

  *Default*: 0

svc
~~~

Check a daemontools supervise service is running.

*Platforms*: FreeBSD, Linux

``path``

  The service directory e.g. ``/var/service/something``

  *Required*: yes

diskspace
~~~~~~~~~

Check the free space on a partition.

*Platforms*: all

``partition``

  The partition to check. On Windows, this is a drive letter (e.g. ``C:``). On non-Windows, this is the mount point (e.g. ``/usr``).

  *Required*: yes

``limit``

  The minimum amount of free space. Give a number in bytes, or suffix with K, M or G for kilo/mega/gigabytes.

  *Required*: yes

http
~~~~

Attempts to fetch a URL via HTTP/S and make sure the return code is 200 OK. Can also verify the body of the page.

*Platforms*: all

``url``

  The URL to open.

  *Required*: yes

``regexp``

  The regexp to match in the page body (only if the response was 200 OK). If the regexp does not match, the monitor reports failure. (See Python's `re` module for syntax.)

  *Required*: no

  *Default*: none

``allowed_codes``

  A comma-separated list of acceptable HTTP status codes *in addition* to 200.

  *Required*: no

  *Default*: none

dns
~~~

Attempts to resolve a DNS record, and optionally check the result. Requires that ``dig`` is available in ``$PATH``.

*Platforms*: POSIX with dig

``record``

  The DNS name to resolve.

  *Required*: yes

``record_type``

  The record type.

  *Required*: no

  *Default*: A

``desired_val``

  The value you want the record to have. For results with newlines (e.g. MX records), format them like this:

  .. code-block:: ini

     desired_val: 10 a.mx.domain.com
       20 b.mx.domain.com
       30 c.mx.domain.com

  Note the leading spaces on the continuation lines.

  *Required*: no

  *Default*: none (i.e. as long as the record resolves the monitor will succeed)

``server``

  The server to send the request to.

  *Required*: no

  *Default*: none (use the system resolver configuration)



