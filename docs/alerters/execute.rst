execute - run external command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. confval:: fail_command

    :type: string
    :required: false

    command to execute when a monitor fails

.. confval:: success_command

    :type: string
    :required: false

    command to execute when a montior recovers

.. confval:: catchup_command

    :type: string
    :required: false

    command to execute when exiting a time period when the alerter couldn't fire, a monitor failed during that time, and hasn't recovered yet. (See the :confval:`delay` configuration option.) If you specify the literal string ``fail_command``, this will share the :confval:`fail_command` configuration value.

You can specify the following variable inside ``{curly brackets}`` to have them substituted when the command is executed:

* ``hostname``: the host the monitor is running on
* ``name``: the monitor's name
* ``days``, ``hours``, ``minutes``, and ``seconds``: the monitor's downtime
* ``failed_at``: the date and time the monitor failed
* ``vitual_fail_count``: the monitor's virtual failure count (number of failed checks - :confval:`tolerance`)
* ``info``: the additional information the monitor recorded about its status
* ``description``: description of what the monitor is checking

You will probably need to quote parameters to the command. For example::

    fail_command=say "Oh no, monitor {name} has failed at {failed_at}"

The commands are executed directly by Python. If you require shell features, such as piping and redirection, you should use something like ``bash -c "..."``. For example::

    fail_command=/bin/bash -c "/usr/bin/printf \"The simplemonitor for {name} has failed on {hostname}.\n\nTime: {failed_at}\nInfo: {info}\n\" | /usr/bin/mailx -A gmail -s \"PROBLEM: simplemonitor {name} has failed on {hostname}.\" email@address"
