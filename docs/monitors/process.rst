process - running process
^^^^^^^^^^^^^^^^^^^^^^^^^

Check for a running process.

.. confval:: process_name

    :type: string
    :required: true

    the process name to check for

.. confval:: min_count

    :type: integer
    :required: false
    :default: ``1``

    the minimum number of matching processes

.. confval:: max_count

    :type: integer
    :required: false
    :default: infinity

    the maximum number of matching processes

.. confval:: username

    :type: string
    :required: false
    :default: any user

    limit matches to processes owned by this user.
