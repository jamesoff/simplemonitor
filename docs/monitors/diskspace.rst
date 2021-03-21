diskspace - free disk space
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Checks the free space on the given partition/drive.

.. confval:: partition

    :type: string
    :required: true

    the partition/drive to check. On Windows, give the drive letter (e.g. :file:`C:`). Otherwise, give the mountpoint (e.g. :file:`/usr`).

.. confval:: limit

    :type: :ref:`bytes<config-bytes>`
    :required: true

    the minimum allowed amount of free space.
