unifi_watchdog - USG failover watchdog
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Checks a Unifi Security Gateway to make sure the failover WAN is healthy. Connects via SSH; the USG must be in your :file:`known_hosts` file. Requires the specified interface to have status ``Running`` and the ping target to be ``REACHABLE``.


.. confval:: router_address

    :type: string
    :required: true

    the address of the USG

.. confval:: router_username

    :type: string
    :required: true

    the username to log in as

.. confval:: router_password

    :type: string
    :required: conditional

    the password to log in with. Required if not using ``ssh_key``.

.. confval:: ssh_key

    :type: string
    :required: conditional

    path to the SSH private key to log in with. Required if not using ``router_password``.

.. confval:: primary_interface

    :type: string
    :required: false
    :default: ``pppoe0``

    the primary WAN interface

.. confval:: secondary_interface

    :type: string
    :required: false
    :default: ``eth2``

    the secondary (failover) WAN interface

.. _unix_service:
