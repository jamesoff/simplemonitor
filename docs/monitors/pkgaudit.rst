pkgaudit - FreeBSD pkg audit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Fails if ``pkg audit`` reports any vulnerable packages installed.

.. confval:: path

    :type: string
    :required: false
    :default: :file:`/usr/local/sbin/pkg`

    the path to the ``pkg`` binary
