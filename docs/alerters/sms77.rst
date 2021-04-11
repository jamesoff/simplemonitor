sms77 - SMS via sms77
^^^^^^^^^^^^^^^^^^^^^

.. include:: ../creds-warning.rst

Send SMSes via the SMS77 service.

.. confval:: api_key

    :type: string
    :required: true

    your API key for SMS77

.. confval:: target

    :type: string
    :required: true

    the target number to send to

.. confval:: sender

    :type: string
    :required: false
    :default: ``SmplMntr``

    the sender to use for the SMS
