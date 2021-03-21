ring_doorbell - Ring doorbell battery
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Check the battery level of a Ring doorbell.

.. confval:: device_name

    :type: string
    :required: true

    the name of the Ring Doorbell to monitor.

.. confval:: minimum_battery

    :type: integer
    :required: false
    :default: ``25``

    the minimum battery percent allowed.

.. confval:: username

    :type: string
    :required: true

    your Ring username (e.g. email address). Accounts using MFA are not supported. You can create a separate user for API access.

.. confval:: password

    :type: string
    :required: true

    your Ring password.

.. warning:: Do not commit credentials to source control!
