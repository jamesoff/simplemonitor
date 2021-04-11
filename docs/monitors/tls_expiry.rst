tls_expiry - TLS cert expiration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Checks an SSL/TLS certificate is not due to expire/has expired. No support for SNI, and does not verify the certificate has the right hostname, chain, etc.

.. note:: This monitor's :ref:`gap<gap>` defaults to 12 hours.

.. warning:: Due to a limitation of the underlying Python modules in use, this does not currently support TLS 1.3.

.. confval:: host

    :type: string
    :required: true

    the hostname to connect to

.. confval:: port

    :type: integer
    :required: false
    :default: ``443``

    the port number to connect on

.. confval:: min_days

    :type: integer
    :required: false
    :default: ``7``

    the minimum allowable number of days until expiry
