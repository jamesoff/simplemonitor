unix_service - generic UNIX service
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generic UNIX service check, by running ``service ... status``.

.. confval:: service

    :type: string
    :required: true

    the name of the service to check

.. confval:: state

    :type: string
    :required: false
    :default: ``running``

    the state of the service; either ``running`` (status command exits 0) or ``stopped`` (status command exits 1).
