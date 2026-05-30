apcupssnmp - APC UPS status via NMC
^^^^^^^^^^^^^^^^^^^^^^^^

Connects directly to an APC UPS with an NMC (Network Management Card) installed, using SNMP.

Currently only supports SNMP v1


.. confval:: host

    :type: string
    :required: true

    The hostname or IP address of the UPS

.. confval:: community

    :type: string
    :required: false
    :default: ``public``

    The SNMP Community name to use when connecting to the UPS.

.. conval:: maxloadpct

    :type: int
    :required: false
    :default: ``80``

    The Load Percentage of the UPS to be OK. A value over 100 will never trigger this warning.

.. conval:: battpctwarn

    :type: int
    :required: false
    :default: ``20``

    The minimum Battery Percentage warning, above this number the battery is deemed OK. Monitor will fail if battery is under 20%. Useful to ensure the monitor stays in a failed state until the battery has recovered enough after a power outage.

.. conval:: runtimemin

    :type: int
    :required: false
    :default: ``10``

    The minimum allowed runtime of the UPS, defaults to 10 (10 minutes). This default is used to allow enough time to trigger shutdown of systems.

.. conval:: textdelimeter

    :type: string
    :required: false
    :default: ``,``

    The text to use to seperate each item in the Details when returned from the test. Defaults to using a comma ','.
    Useful if you want to use this text in another system, or make it easier to read
