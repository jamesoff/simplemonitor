seq - seq log server
^^^^^^^^^^^^^^^^^^^^

Sends the status of monitors to a **Seq** log server. See https://datalust.co/seq for more information on Seq.

.. confval:: endpoint

    :type: string
    :required: true

    Full URI for the endpoint on the seq server, for example ``http:://localhost:5341/api/events/raw``.
    See the raw `API ingestion documentation <https://docs.datalust.co/docs/server-http-api#api>` for the curent endpoint URI.

.. confval:: timeout

    :type: int
    :required: false
    :default: ``5``

    Timeout for HTTP request to seq
