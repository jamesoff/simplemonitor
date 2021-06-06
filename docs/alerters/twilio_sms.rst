twilio_sms - SMS via Twilio
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: ../creds-warning.rst

Send SMSes via the Twilio service.

.. confval:: account_sid

    :type: string
    :required: true

    your account SID for Twilio

.. confval:: auth_token

    :type: string
    :required: true

    your auth token for Twilio

.. confval:: target

    :type: string
    :required: true

    the target number to send to. Format should be ``+`` followed by a country code and then the phone number

.. confval:: sender

    :type: string
    :required: false
    :default: ``SmplMntr``

    the sender to use for the SMS. Should be a number in the same format as the target parameter, or you may be able to use an `alphanumberic ID <https://www.twilio.com/docs/sms/send-messages#use-an-alphanumeric-sender-id>`_.
