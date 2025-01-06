network - remote SimpleMonitor logging
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: ../creds-warning.rst

This logger is used to send status reports of all monitors to a remote
instance. The remote instance must be configured to listen for connections. The
``key`` parameter is a shared secret used to generate a hash of the network traffic
so the receiving instance knows to trust the data.

.. warning:: Note that the traffic is not encrypted, just given a hash to validate it.

The remote instance will need the ``remote``, ``remote_port``, and ``key`` :ref:`configuration values<config-remote>` set.

If you want the remote instance to handle alerting for this instance's monitors, you need to set the :ref:`remote_alert<monitor-remote-alert>` option on your monitors. This is a good candidate to go the ``[defaults]`` section of your monitors config file.

.. confval:: host

    :type: string
    :required: true

    the remote hostname/IP to send to

.. confval:: port

    :type: string
    :required: true

    the remote port to connect to

.. confval:: key

    :type: string
    :required: true

    the shared secret to validate communications

.. confval:: client_name

    :type: string
    :required: false

    the name to introduce ourselves as to the remote host as. If unset, it will know us by the IP it sees us connect from.
