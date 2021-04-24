tls_expiry - TLS cert expiration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Checks an SSL/TLS certificate is not due to expire/has expired.

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

.. confval:: sni

    :type: string
    :required: false

    the hostname to send during TLS handshake for SNI. Use if you are serving multiple certificates from the same host/port. If empty, will just get the default certificate from the server
