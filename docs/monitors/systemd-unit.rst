systemd-unit - systemd unit check
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Monitors a systemd unit status, via dbus. You may want the :ref:`unix_service<unix_service>` monitor instead if you just want to ensure a service is running.

.. confval:: name

    :type: string
    :required: true

    the name of the unit to monitor

.. confval:: load_states

    :type: comma-separated list of string
    :required: false
    :default: ``loaded``

    desired load states for the unit

.. confval:: active_states

    :type: comma-separated list of string
    :required: false
    :default: ``active,reloading``

    desired active states for the unit

.. confval:: sub_states

    :type: comma-separated list of string
    :required: false
    :default: none

    desired sub states for the service
