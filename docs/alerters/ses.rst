ses - email via Amazon Simple Email Service
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: ../creds-warning.rst

.. include:: ../aws-boilerplate.rst

You will need to `verify an address or domain`_.

.. _verify an address or domain: https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html

.. confval:: from

    :type: string
    :required: true

    the email address to send from

.. confval:: to

    :type: string
    :required: true

    the email address to send to

.. include:: ../aws-confvals.rst
