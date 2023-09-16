command - run an external command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run a command, and optionally verify its output. If the command exits non-zero, this monitor fails.

.. confval:: command

    :type: string
    :required: true

    the command to run.

.. confval:: result_regexp

    :type: string (regular expression)
    :required: false
    :default: none

    if supplied, the output of the command must match else the monitor fails.

.. confval:: result_max

    :type: integer
    :required: false

    if supplied, the output of the command is evaluated as an integer and if greater than this, the monitor fails. If the output cannot be converted to an integer, the monitor fails.

.. confval:: show_output

    :type: boolean
    :required: false

    if set to true, the output of the command will be captured as the message with a successful test.
