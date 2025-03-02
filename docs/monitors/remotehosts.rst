remotehosts - monitor remote simplemonitors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This monitor inspects the state of the local simplemonitor instance to check expected remotes are sending data to it.

.. warning:: At startup, simplemonitor doesn't know any remote hosts. They'll only be known once they've connected once, which means this monitor may fail initially. Consider using the ``tolerance`` option to reduce false positives.

.. confval:: hosts

    :type: comma-separated list of string
    :required: true

    the remote hosts to expect. This will need to be a list of IPs as simplemontitor doesn't reverse-lookup connections. However, if you want to give names to your remotes, you can use the ``custom_name`` property of the network logger and then specify that here.

.. confval:: max_age

    :type: int
    :required: false
    :default: 300

    the maximum time in seconds since a remote host last contacted us before it's considered missing

.. note:: Note that depending on your OS/configuration, you may see IPv4 IPs with a ``::ffff:`` prefix.

.. tip:: This monitor reports both missing and unexpected remotes, so you can use that to see what should go in your configuration.
