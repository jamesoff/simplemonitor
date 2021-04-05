mqtt - send to MQTT server
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: ../creds-warning.rst

Sends monitor status to an MQTT server. Supports Home Assistant specifics (see https://www.home-assistant.io/docs/mqtt/discovery/ for more information).

.. confval:: host

    :type: string
    :required: true

    the hostname/IP to connect to

.. confval:: port

    :type: integer
    :required: false
    :default: ``1883``

    the port to connect on

.. confval:: hass

    :type: boolean
    :required: false
    :default: false

    enable Home Assistant specific features for MQTT discovery

.. confval:: topic

    :type: string
    :required: false
    :default: see below

    the MQTT topic to post to. By default, if ``hass`` is not enabled, uses ``simplemonitor``, else ``homeassistant/binary_sensor``

.. confval:: username

    :type: string
    :required: false

    the username to use

.. confval:: password

    :type: string
    :required: false

    the password to use
