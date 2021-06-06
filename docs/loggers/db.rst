.. _logger-db:

db - sqlite log of results
^^^^^^^^^^^^^^^^^^^^^^^^^^

Logs results to a SQLite database. The results are written to a table named ``results``.

If you want to have a SQLite snapshot of the current state of the monitors (not a log of results), see the :ref:`dbstatus<logger-dbstatus>` logger.

Automatically create the database schema.

.. confval:: path

    :type: string
    :required: true

    the path to the database file to use
