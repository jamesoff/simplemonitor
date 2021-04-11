host - ping a host
^^^^^^^^^^^^^^^^^^

Check a host is pingable.

.. tip:: This monitor relies on executing the ``ping`` command provided by your OS. It has known issues on non-English locales on Windows. You should use the :ref:`ping<ping>` monitor instead. The only reason to use this one is that it does not require SimpleMonitor to run as root.

.. confval:: host

    :type: string
    :required: true

    the hostname/IP to ping

.. confval:: ping_regexp

    :type: regexp
    :required: false
    :default: automatic

    the regexp which matches a successful ping. You may need to set this to use this monitor in a non-English locale.

.. confval:: time_regexp

    :type: regexp
    :required: false
    :default: automatic

    the regexp which matches the ping time in the output. Must set a match group named ``ms``. You may need to set this as above.
