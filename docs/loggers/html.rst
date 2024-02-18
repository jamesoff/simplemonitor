.. _logger-html:

html - HTML status page
^^^^^^^^^^^^^^^^^^^^^^^

.. include:: ../creds-warning.rst

Writes an HTML status page. Can optionally display a map.

The supplied template includes JavaScript to notify you if the page either doesn’t auto-refresh, or if SimpleMonitor has stopped updating it. This requires your machine running SimpleMonitor and the machine you are browsing from to agree on what the time is (timezone doesn’t matter)! The template is written using Jinja2.

You can use the ``upload_command`` setting to specify a command to push the generated files to another location (e.g. a web server, an S3 bucket etc). I'd suggest putting the commands in a script and just specifying that script as the value for this setting.

.. confval:: filename

    :type: string
    :required: true

    the html file to output. Will be stored in the ``folder``

.. confval:: folder

    :type: string
    :required: false
    :default: ``html``

    the folder to write the output file(s) to. Must exist.

.. confval:: copy_resources

    :type: boolean
    :required: false
    :default: true

    if true, copy supporting files (CSS, images, etc) to the ``folder``

.. confval:: source_folder

    :type: string
    :required: false

    the path to find the template and supporting files in. Defaults to those contained in the package. (In the package source, they are in :file:`simplemonitor/html/`.)

.. confval:: upload_command

    :type: string
    :required: false

    if set, a command to execute each time the output is updated to e.g. upload the files to an external webserver

.. confval:: map

    :type: boolean
    :required: false

    set to true to enable the map display instead of the table. You must set the :ref:`gps<monitor-gps>` value on your Monitors for them to show up!

.. confval:: map_start

    :type: comma-separated list of float
    :required: false

    three comma-separated values: the latitude the map display should start at, the longitude, and the zoom level. A good starting value for the zoom is probably between 10 and 15.
