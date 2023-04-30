46elks - 46elks notifications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: ../creds-warning.rst

You will need to register for an account at 46elks_.

.. _46elks: https://46elks.com/

.. confval:: username

    :type: string
    :required: true

    your 46wlks username

.. confval:: password

    :type: string
    :required: true

    your 46wlks password

.. confval:: target

    :type: string
    :required: true

    46elks target value

.. confval:: sender

    :type: string
    :required: false
    :default: ``SmplMntr``

    your SMS sender field. Start with a ``+`` if using a phone number.

.. confval:: api_host

    :type: string
    :required: false
    :default: ``api.46elks.com``

    API endpoint to use

.. confval:: timeout

    :type: int
    :required: false
    :default: ``5``

    Timeout for HTTP request
