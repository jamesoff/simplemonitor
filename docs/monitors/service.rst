service - Windows Service
^^^^^^^^^^^^^^^^^^^^^^^^^

Checks a Windows service to make sure it's in the correct state.

.. confval:: service

    :type: string
    :required: true

    the short name of the service to monitor (this is the "Service Name" on the General tab of the service Properties in the Services MMC snap-in).

.. confval:: want_state

    :type: string
    :required: false
    :default: ``RUNNING``

    the required status for the service. One of:

    * ``RUNNING``
    * ``STOPPED``
    * ``PAUSED``
    * ``START_PENDING``
    * ``PAUSE_PENDING``
    * ``CONTINUE_PENDING``
    * ``STOP_PENDING``

.. tip:: version 1.9 and earlier had a **host** parameter, which is no longer used.
