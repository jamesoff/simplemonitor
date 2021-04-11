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

.. include:: ../aws-confvals.rst
