rc - FreeBSD rc service
^^^^^^^^^^^^^^^^^^^^^^^

Checks a FreeBSD-style service is running, by running its rc script (in /usr/local/etc/rc.d) with the status command.

.. tip:: You may want the :ref:`unix_service<unix_service>` monitor for a more generic check.

.. confval:: service

    :type: string
    :required: true

    the name of the service to check. Should be the name of the rc.d script in :file:`/usr/local/etc/rc.d`. Any trailing ``.sh`` is optional and added if needed.

.. confval:: path

    :type: string
    :required: false
    :default: :file:`/usr/local/etc/rc.d`

    the path of the folder containing the rc script.

.. confval:: return_code

    :type: integer
    :required: false
    :default: ``0``

    the required return code from the script
