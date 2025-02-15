.. _gmirror:

gmirror - check gmirror array status
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Shells out to ``gmirror`` to check array status

.. confval:: array_device

   :type: string
   :required: true

   The device to check (e.g., ``gm0``).

.. confval:: expected_disks

   :type: int
   :required: true

   Number of expected members of the given array.
