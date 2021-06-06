unifi_failover - USG failover WAN status
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Checks a Unifi Security Gateway for failover WAN status. Connects via SSH; the USG must be in your :file:`known_hosts` file. Requires the specified interface to have the carrier up, a gateway, and not be in the ``failover`` state.

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

.. confval:: check_interface

    :type: string
    :required: false
    :default: ``eth2``

    the interface which should be ready for failover.
