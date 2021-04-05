.. _logger-dbstatus:

dbstatus - sqlite status snapshot
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Stores a snapshot of monitor status in a SQLite database. The statuses are written to a table named ``status``.

If you want to have a SQLite log of results (not a snapshot), see the :ref:`db<logger-db>` logger.

Automatically creates the database schema.

.. confval:: path

    :type: string
    :required: true

    the path to the database file to use
