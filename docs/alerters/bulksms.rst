bulksms - SMS via BulkSMS
^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning:: Do not commit your credentials to a public repo!

.. confval:: sender

    :type: string
    :required: false
    :default: ``SmplMntr``

    who the SMS should appear to be from. Max 11 chars, and best to stick to alphanumerics.

.. confval:: username

    :type: string
    :required: true

    your BulkSMS username

.. confval:: password

    :type: string
    :required: true

    your BulkSMS password

.. confval:: target

    :type: string
    :required: true

    the number to send the SMS to. Specify using country code and number, with no ``+`` or international prefix. For example, ``447777123456`` for a UK mobile.
