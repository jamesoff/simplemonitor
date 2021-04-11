email - send via SMTP
^^^^^^^^^^^^^^^^^^^^^

.. warning:: Do not commit your credentials to a public repo!

.. confval:: host

    :type: string
    :required: true

    the email server to connect to

.. confval:: port

    :type: integer
    :required: false
    :default: ``25``

    the port to connect on

.. confval:: from

    :type: string
    :required: true

    the email address to give as the sender

.. confval:: to

    :type: string
    :required: true

    the email address to send to. You can specify multiple addresses by separating with ``;``.

.. confval:: cc

    :type: string
    :required: false

    the email address to cc to. You can specify multiple addresses by separating with ``;``.

.. confval:: username

    :type: string
    :required: false

    the username to log in to the SMTP server with

.. confval:: password

    :type: string
    :required: false

    the password to log in to the SMTP server with

.. confval:: ssl

    :type: string
    :required: false

    specify ``starttls` to use StartTLS. Specify ``yes`` to use SMTP SSL. Otherwise, no SSL is used at all.
