http - fetch and verify a URL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Attempts to fetch a URL and makes sure the HTTP return code is (by default) 200/OK. Can also match the content of the page to a regular expression.

.. confval:: method

    :type: string
    :required: true
    :default: `GET`

    The method used in the HTTP request: `HEAD` `GET` `POST`

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

.. confval:: allow_redirects

    :type: bool
    :required: false
    :default: true

    Follow redirects

.. confval:: username

    :type: str
    :required: false
    :default: none

    Username for http basic auth

.. confval:: password

    :type: str
    :required: false
    :default: none

    Password for http basic auth

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

.. tip:: You can set the headers globally in monitors.ini [defaults] section

.. confval:: headers

    :type: JSON map as string
    :required: false
    :default: none

    JSON map of HTTP header names and values to add to the request

.. warning:: Use only one of the following options - either json OR data.

.. confval:: data

    :type: string
    :required: false
    :default: none

    Data to add to the POST request

.. confval:: json

    :type: JSON as string
    :required: false
    :default: none

    JSON to add to the POST request
