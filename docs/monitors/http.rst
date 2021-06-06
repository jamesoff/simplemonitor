http - fetch and verify a URL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Attempts to fetch a URL and makes sure the HTTP return code is (by default) 200/OK. Can also match the content of the page to a regular expression.

.. confval:: url

    :type: string
    :required: true

    the URL to open

.. confval:: regexp

    :type: regexp
    :required: false
    :default: none

    the regexp to look for in the body of the response

.. confval:: allowed_codes

    :type: comma-separated list of integer
    :required: false
    :default: `200`

    a list of acceptable HTTP status codes

.. confval:: verify_hostname

    :type: boolean
    :required: false
    :default: true

    set to false to disable SSL hostname verification (e.g. with self-signed certificates)

.. confval:: timeout

    :type: integer
    :required: false
    :default: ``5``

    the timeout in seconds for the HTTP request to complete

.. confval:: headers

    :type: JSON map as string
    :required: false
    :default: ``{}``

    JSON map of HTTP header names and values to add to the request
