.. _ping:

ping - ping a host
^^^^^^^^^^^^^^^^^^

Pings a host to make sure it’s up. Uses a Python ping module instead of calling out to an external app, but needs to be run as root.

.. confval:: host

   :type: string
   :required: true

   the hostname or IP to ping

.. confval:: timeout

    :type: int
    :required: false
    :default: ``5``

    the timeout for the ping in seconds

.. confval:: count

    :type: int
    :required: false
    :default: ``1``

    the number of pings to send
