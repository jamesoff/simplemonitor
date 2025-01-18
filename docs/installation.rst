.. _Installation:

Installation
============

SimpleMonitor is available via `PyPi <https://pypi.org/project/simplemonitor>`_::

   pip install simplemonitor

.. tip:: You may want to install it in a virtualenv, or you can use `pipx <https://pipxproject.github.io/pipx/>`_
   which automatically manages virtualenvs for command-line tools.

Create the configuration files: ``monitor.ini`` and ``monitors.ini``. See
:ref:`Configuration`.

.. warning:: I know the configuration file names are dumb, sorry.

If you are using Debian 13 (Trixie) or newer, or Ubuntu 23.04 (Mantic Minotaur) or newer, SimpleMonitor is available in the official repositories and can be installed using::

   sudo apt install simplemonitor

If using Debian/Ubuntu packages the configuration is in
``/etc/simplemonitor/`` and SimpleMonitor can be managed via systemd::

  sudo systemctl {restart,start,stop,status} simplemonitor

Running
-------

Just run::

   simplemonitor

SimpleMonitor does not fork. For best results, run it with a service
management tool such as daemontools, supervisor, or systemd. You can find
some sample configurations for this purpose `on GitHub
<https://github.com/jamesoff/simplemonitor/tree/develop/scripts>`_.

SimpleMonitor will look for its configuration files in the current working
directory. You can specify a different configuration file using ``-f``.

You can verify the configuration files syntax with ``-t``.

By default, SimpleMonitor's output is limited to errors and other issues, and
it emits a ``.`` character every two loops. Use ``-H`` to disable the latter,
and ``-v``, ``-d`` and ``-q`` (or ``-l``) to control the former.

If you are using something like systemd or multilog which add their own
timestamps to the start of the line, you may want ``--no-timestamps`` to
avoid having unnecessary timestamps added.

Command Line Options Reference
------------------------------

**General options**

  -h, --help            show help message and exit
  --version             show version number and exit

**Execution options**

  -p PIDFILE, --pidfile PIDFILE
                        Write PID into this file
  -N, --no-network      Disable network listening socket (if enabled in config)
  -f CONFIG, --config CONFIG
                        configuration file (this is the main config; you also need monitors.ini (default filename)
  -j THREADS, --threads THREADS
                        number of threads to run for checking monitors (default is number of CPUs detected)

**Output options**
  -v, --verbose         Alias for ``--log-level=info``
  -q, --quiet           Alias for ``--log-level=critical``
  -d, --debug           Alias for ``--log-level=debug``
  -H, --no-heartbeat    Omit printing the ``.`` character when running checks
  -l LOGLEVEL, --log-level LOGLEVEL
                        Log level: critical, error, warn, info, debug
  -C, --no-colour, --no-color
                        Do not colourise log output
  --no-timestamps       Do not prefix log output with timestamps

**Testing options**
  -t, --test            Test config and exit

These options are really for testing SimpleMonitor itself, and you probably don't need them.

  -1, --one-shot        Run the monitors once only, without alerting. Require monitors without "fail" in the name to succeed. Exit zero
                        or non-zero accordingly.
  --loops LOOPS         Number of iterations to run before exiting
  --dump-known-resources
                        Print out loaded Monitor, Alerter and Logger types
