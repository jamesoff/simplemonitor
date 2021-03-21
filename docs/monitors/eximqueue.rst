eximqueue - Exim queue size
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Checks the output of ``exigrep`` to make sure the queue isn't too big.

.. confval:: max_length

    :type: integer
    :required: false
    :default: ``1``

    the maximum acceptable queue length

.. confval:: path

    :type: string
    :required: false
    :default: ``/usr/local/sbin``

    the path containing the ``exigrep`` binary
