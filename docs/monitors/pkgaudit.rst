pkgaudit - FreeBSD pkg audit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Fails if ``pkg audit`` reports any vulnerable packages installed.

.. confval:: path

    :type: string
    :required: false
    :default: :file:`/usr/local/sbin/pkg`

    the path to the ``pkg`` binary

.. confval:: ignore

    :type: comma-separated list of string
    :required: false

    a list of VuXML identifiers to ignore. These should be the
    GUID-style identifiers (they appear in the URL), for
    example ``613d0f9e-d477-11f0-9e85-03ddfea11990``.
