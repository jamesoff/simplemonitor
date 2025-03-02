svc - daemontools service
^^^^^^^^^^^^^^^^^^^^^^^^^

Checks a daemontools ``supervise``-managed service is running.

.. confval:: path

    :type: string
    :required: true

    the path to the service's directory (e.g. :file:`/var/service/something`)

.. confval:: minimum_uptime

   :type: int
   :required: false
   :default: ``0``

   the minimum number of seconds the service needs to be up for
