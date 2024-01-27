Configuration
=============

The main configuration lives in :file:`monitor.ini`. By default, SimpleMonitor will
look for it in the working directory when launched. To specify a different
file, use the ``-f`` option.

The format is fairly standard "INI"; section names are lowercase in ``[square
brackets]``, and values inside the sections are defined as ``key=value``. You
can use blank lines to space things out, and comments start with ``#``.

Section names and option values, but not option names, support environment
variable injection. To include the value of an environment variable, use
``%env:VARIABLE%``, which will inject the value of ``$VARAIBLE`` from the
environment. You can use this to share a common configuration file across
multiple hosts, for example.

This main configuration file contains the global settings for SimpleMonitor,
plus the logging and alerting configuration. A separate file, by default
:file:`monitors.ini`, contains the monitor configuration. You can specify a
different monitors configuration file using a directive in the main
configuration.

.. warning:: I know the configuration file names are dumb, sorry.

.. _config-bytes:

Configuration value types
-------------------------

Values which take **bool** accept ``1``, ``yes``, and ``true`` as truthy, and
everything else as falsey.

Values which take **bytes** accept suffixes of ``K``, ``M``, or ``G`` for
kibibytes, mibibytes or gibibytes, otherwise are just a number of bytes.

``monitor.ini``
---------------

This file must contain a ``[monitor]`` section, which must contain at least the ``interval`` setting.

``[monitor]`` section
^^^^^^^^^^^^^^^^^^^^^

.. confval:: interval

   :type: integer
   :required: true

   defines how many seconds to wait between running all the monitors. Note that
   the time taken to run the monitors is not subtracted from the interval, so
   the next iteration will run at interval + time_to_run_monitors seconds.

.. confval:: monitors

    :type: string
    :required: false
    :default: ``monitors.ini``

    the filename to load the monitors themselves from. Relative to the cwd, not
    the path of this configuration file.

    If you want to use only ``monitors_dir``, set this to nothing (``monitors=``).



.. confval:: monitors_dir

    :type: string
    :required: false

    a directory to scan for ``*.ini`` files which are merged with the main
    monitors config file. Files are loaded in lexicographic order, and if a
    monitor name is reused, the last definition wins. Relative to the cwd, not
    the path of this configuration file.

    The main ``monitors`` file is always loaded first.

.. confval:: pidfile

    :type: string
    :required: false
    :default: none

    the path to write a pidfile to.

.. _config-remote:

.. confval:: remote

    :type: bool
    :required: false
    :default: false

    enables the listener for receiving data from remote instances. Can be
    overridden to disabled with ``-N`` command line option.

.. confval:: remote_port

    :type: integer
    :required: if ``remote`` is enabled

    the TCP port to listen on for remote data

.. confval:: key

    :type: string
    :required: if ``remote`` is enabled

    shared secret for validating data from remote instances.

.. confval:: bind_host

    :type: string
    :required: false
    :default: ``0.0.0.0`` (all interfaces)

    the local IP address to listen on, if ``remote`` is enabled.

.. confval:: hup_file

    :type: string
    :required: false
    :default: none

    a file to watch the modification time on. If the modification time increases, SimpleMonitor :ref:`reloads its configuration<Reloading>`.

    .. tip:: SimpleMonitor will reload if it receives SIGHUP; this option is useful for platforms which don't have that.

.. confval:: bind_host

    :type: string
    :required: false
    :default: all interfaces

    the local address to bind to for remote data

``[reporting]`` section
^^^^^^^^^^^^^^^^^^^^^^^

.. confval:: loggers

    :type: comma-separated list of string
    :required: false
    :default: none

    the names of the loggers you want to use. Each one must be a ``[section]`` in this configuration file.

    See Loggers for the common options and list of Alerters with their configurations.

.. confval:: alerters

    :type: comma-separated list of string
    :required: false
    :default: none

    the names of the alerters you want to use. Each one must be a ``[section]`` in this configuration file.

    See Alerters for the common options and list of Alerters with their configurations.

``monitors.ini``
----------------

This file only contains monitors. Each monitor is a ``[section]`` in the file,
with the section name giving the monitor its name. The name ``defaults`` is
reserved, and can be used to specify default values for options. Each monitor's
individual configuration overrides the defaults.

See Monitors for the common options and list of Monitors with their configurations.

Example configuration
---------------------

This is an example pair of configuration files to show what goes where. For more examples, see :ref:`Config examples`.

:file:`monitor.ini`:

.. code-block:: ini

   [monitor]
   interval=60

   [reporting]
   loggers=logfile
   alerters=email,sms

   # write a log file with the state of each monitor, each time
   [logfile]
   type=logfile
   filename=monitor.log

   # email me when monitors fail or succeed
   [email]
   type=email
   host=mailserver.example.com
   from=monitor@example.com
   to=admin@example.com

   # send me an SMS after a monitor has failed 10 times in a row
   [sms]
   type=bulksms
   username=some-username
   password=some-password
   target=+447777123456
   limit=10

:file:`monitors.ini`:

.. code-block:: ini

   # check the webserver pings
   [www-ping]
   type=ping
   host=www.example.com

   # check the webserver answers https; don't bother checking if it's not pinging
   [www-http]
   type=http
   url=https://www.example.com
   depend=www-ping

   # check the root partition has at least 1GB of free space
   [root-diskspace]
   type=diskspace
   partition=/
   limit=1G

.. _Reloading:

Reloading
---------

You can send SimpleMonitor a SIGHUP to make it reload its configuration. On
platforms which don't have that (e.g. Windows), you can specify a file to
watch. If the modification time of the file changes, SimpleMonitor will reload
its configuration.

Reloading will pick up a change to ``interval`` but no other configuration in
the ``[monitor]`` section. Monitors, Alerters and Loggers are reloaded. You can
add and remove them, and change their configurations, but not change their
types. (To change a type, first remove it from the configuration and reload,
then add it back in.)
