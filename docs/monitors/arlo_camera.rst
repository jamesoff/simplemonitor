arlo_camera - Arlo camera battery level
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Checks Arlo camera battery level is high enough.

.. confval:: username

    :type: string
    :required: true

    Arlo username

.. confval:: password

    :type: string
    :required: true

    Arlo password

.. confval:: device_name

    :type: string
    :required: true

    the device to check (e.g. ``Front Camera``)

.. confval:: base_station_id

    :type: integer
    :required: false
    :default: ``0``

    the number of your base station. Only required if you have more than one. It's an array index, but figuring out which is which is an exercise left to the reader.
