loadavg - load average
^^^^^^^^^^^^^^^^^^^^^^

Check the load average on the host.

.. confval:: which

    :type: integer
    :required: false
    :default: ``1``

    the load average to monitor. ``0`` = 1min, ``1`` = 5min, ``2`` = 15min

.. confval:: max

    :type: float
    :required: false
    :default: ``1.00``

    the maximum acceptable load average
