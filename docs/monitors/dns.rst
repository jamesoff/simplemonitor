dns - resolve record
^^^^^^^^^^^^^^^^^^^^

Attempts to resolve the DNS record, and optionally checks the result. Requires ``dig`` to be installed and on the PATH.

.. confval:: record

    :type: string
    :required: true

    the DNS name to resolve

.. confval:: record_type

    :type: string
    :required: false
    :default: ``A``

    the type of record to request

.. confval:: desired_val

    :type: string
    :required: false

    if not given, this monitor simply checks the record resolves.

    Give the special value ``NXDOMAIN`` to check the record **does not** resolve.

    If you need to check a multivalue response (e.g. MX records), format them like this (note the leading spaces on the continuation lines):

    .. code-block:: ini

        desired_val=10 a.mx.domain.com
          20 b.mx.domain.com
          30 c.mx.domain.com

.. confval:: server

    :type: string
    :required: false

    the server to send the request to. If not given, uses the system default.
