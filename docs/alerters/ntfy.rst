ntfy - ntfy notifications
^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: ../creds-warning.rst

Send alerts using the ntfy_ service.

.. _ntfy: https://ntfy.sh

.. confval:: topic

    :type: string
    :required: true

    the ntfy topic to send to

.. confval:: priority

    :type: str or int
    :required: false
    :default: ``default``

    the priority to use for notifications. an int 1 to 5 (1 is lowest, 5 is highest), or one of ``max``, ``high``, ``default``, ``low``, ``min``

.. confval:: tags

    :type: string
    :required: false

    the tags to add to the notification. A comma-separated list of strings

.. confval:: token

    :type: string
    :required: false

    your token for ntfy, if required

.. confval:: server

    :type: string
    :required: false
    :default: ``https://ntfy.sh``

    the server to send to

.. confval:: timeout

    :type: int
    :required: false
    :default: ``5``

    Timeout for HTTP request

.. confval:: icon_prefix

    :type: bool
    :required: false
    :default: false

    Prefix the subject line with an icon dependent on the result (failed/succeeded)

.. confval:: icon_failed

    :type: str
    :required: false
    :default: ``274C``

    Unicode code for the "failed" icon. The code is often provided as "U+<code>" (e.g. ``U+274C``). The default icon for the failed status is ❌.

.. confval:: icon_succeeded

    :type: str
    :required: false
    :default: ``2705``

    Unicode code for the "succeeded" icon. The code is often provided as "U+<code>" (e.g. ``U+2705``). The default icon for the failed status is ✅.
