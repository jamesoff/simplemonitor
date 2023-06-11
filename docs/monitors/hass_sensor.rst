hass_sensor - Home Automation Sensors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This monitor checks for the existence of a home automation sensor.

.. confval:: url

    :type: string
    :required: true

    API URL for the monitor

.. confval:: sensor

    :type: string
    :required: true

    the name of the sensor

.. confval:: token

    :type: string
    :required: true

    API token for the sensor

.. confval:: timeout

    :type: int
    :required: false
    :default: ``5``

    Timeout for HTTP request to HASS
