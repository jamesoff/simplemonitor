healthchecks - notifications
^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: ../creds-warning.rst

You will need to be registered at healthchecks.io_.

.. _healthchecks.io: https://healthchecks.io/

.. note:: To enable posting to Healthchecks Pinging API - a monitor MUST have ``slug`` defined.

.. note:: You need to generate ``ping_key`` for each of your project.

.. confval:: token

    :type: string
    :required: true

    Your project ping_key

.. confval:: create

    :type: bool
    :required: true

    Add create=1 param to support Auto provisioning - creating new checks for undeclared slugs

.. warning:: You might need to adjust some settings_ for the newly created checks.

.. _settings: https://healthchecks.io/docs/autoprovisioning/

.. confval:: headers

    :type: JSON map as string
    :required: false
    :default: ``{"User-Agent": "SimpleMonitor"}``

    Add custom headers for the POST request

.. confval:: timeout

    :type: int
    :required: false
    :default: ``5``

    Timeout for HTTP request
