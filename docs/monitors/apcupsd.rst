apcupsd - APC UPS status
^^^^^^^^^^^^^^^^^^^^^^^^

Uses an existing and configured ``apcupsd`` installation to check the UPS status. Any status other than ``ONLINE`` is a failure.

.. confval:: path

    :type: string
    :required: false
    :default: none

    the path to the :file:`apcaccess` binary. On Windows, defaults to :file:`C:\\apcupsd\\bin`. On other platforms, looks in ``$PATH``.
