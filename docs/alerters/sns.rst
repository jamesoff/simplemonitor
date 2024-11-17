sns - Amazon Simple Notification Service
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: ../creds-warning.rst

.. include:: ../aws-boilerplate.rst

Note that not all regions with SNS also support sending SMS.

.. confval:: topic

    :type: string
    :required: yes, if ``number`` is not given

    the ARN of the SNS topic to publish to. Specify this, or ``number``, but not both.

.. confval:: number

    :type: string
    :required: yes, if ``topic`` is not given

    the phone number to SMS. Give the number as country code then number, without a ``+`` or other international access code. For example, ``447777123456`` for a UK mobile. Specify this, or ``topic``, but not both.

.. confval:: sender_id

    :type: string
    :required: no
    :default: ``SmplMntr``

    the sender ID to use when sending SMSes. See the SenderID documentation in the SNS docs: https://docs.aws.amazon.com/sns/latest/dg/sms_sending-overview.html#sms_publish-to-phone

.. include:: ../aws-confvals.rst
