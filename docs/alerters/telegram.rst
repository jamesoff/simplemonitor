telegram - send to a chat
^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: ../creds-warning.rst

.. confval:: token

    :type: string
    :required: true

    the token to access Telegram

.. confval:: chat_id

    :type: string
    :required: true

    the chat id to send to

.. confval:: timeout

    :type: int
    :required: false
    :default: ``5``

    Timeout for HTTP request to Telegram
