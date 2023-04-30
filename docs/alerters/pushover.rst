pushover - notifications
^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: ../creds-warning.rst

You will need to be registered at pushover_.

.. _pushover: https://pushover.net/

.. confval:: user

    :type: string
    :required: true

    your pushover user key

.. confval:: token

    :type: string
    :required: true

    your pushover app token

.. confval:: timeout

    :type: int
    :required: false
    :default: ``5``

    Timeout for HTTP request
