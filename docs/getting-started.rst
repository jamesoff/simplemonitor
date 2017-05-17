Getting Started
===============

* Download the code
* Write your configuration files
* Run the code

Downloading the code
--------------------

Blah


Writing configuration files
---------------------------

There are two configuration files to write: ``monitor.ini`` which defines overall behaviour including alerting and logging, and ``monitors.ini`` which defines the actual monitors.

Running SimpleMonitor
---------------------

* ``python monitor.py``

That was easy.

If you want to hide all output except errors, use the -q option. If you want more verbose blah about what’s happening, use -v.

On non-Windows, SimpleMonitor runs very nicely under something like daemontools or supervisor. You just need a run file a bit like this:

.. code:: bash

    #!/bin/sh

    cd /usr/local/monitor && exec /usr/local/bin/python monitor.py -q

On Windows hosts, you’ll have to leave it running in a Command Prompt for now; I haven’t gotten round to making it run as a service.

For help on (the scarce) command line options, run ``python monitor.py -h``.

