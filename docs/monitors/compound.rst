compound - combine monitors
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Combine (logical-and) multiple monitors. By default, if any monitor in the list is OK, this monitor is OK. If they all fail, this monitor fails. To change this limit use the ``min_fail`` setting.

.. warning:: Do not specify the other monitors in this monitor's ``depends`` setting. The dependency handling for compound monitors is a special case and done for you.

.. confval:: monitors

    :type: comma-separated list of string
    :required: true

    the monitors to combine

.. confval:: min_fail

    :type: integer
    :required: false
    :default: the number of monitors in the list

    the number of monitors from the list which should be failed for this monitor to fail. The default is that all the monitors must fail.
