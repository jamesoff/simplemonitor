filestat - file size and age
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Examines a file's size and age. If neither of the age/size values are given, simply checks the file exists.

.. confval:: filename

    :type: string
    :required: true

    the path of the file to monitor.

.. confval:: maxage

    :type: integer
    :required: false

    the maximum allowed age of the file in seconds. If not given, not checked.

.. confval:: minsize

    :type: :ref:`bytes<config-bytes>`
    :required: false

    the minimum allowed size of the file in bytes. If not given, not checked.
