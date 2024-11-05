remote_ssh - Monitor Remote Entities With SSH
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``remote_ssh`` is a generic Monitor intended to be used for remote machines that do not have Simplemonitor installed.
It connects with ``ssh`` to run a remote command, then parses the reply and monitors the result.

.. warning::
    This Monitor uses bare `ssh` commands, in the context of the user they are run againt. This means that you can break everything and a little bit more if you are not careful.

    You should also consider the security risk of having an SSH private key on the monotoring machine. And while we are at the topic of cybersecurity, you should ensure that the SSH command is not injected (this is not liklely if you do not dynamically generate `monitors.ini`)


.. tip::
    This Monitor rejects connections to hosts with unknown keys; you should arrange for the host key to be known to the user Simplemonitor is running as in advance (e.g. by sshing to the target hosts once or placing the key in ``known_hosts`` directly).

The sequence of this Monitor is to send to ``ssh_username@target_host:target_port`` the ``command`` via SSH, retrieve the output and parse it with ``regex`` to extract a value.

This value is then compared with ``target_value`` with ``operator``. A failed comparison raises an alert.

.. info::
    This Monitor is limited in the edge cases it can manage. If you use a command with a predictible output and a proper regex you are good. If you start to tinker or have a regex that is not solid you may crash your Monitor (which just means you have to correct something)


.. confval:: description

    :type: string
    :required: false

    The description of the Monitor which is sent back upon configuring an instance of this Monitor. Fallsback to a generic description.

.. confval:: target_hostname

    :type: string
    :required: true

    The remote host to run the command on.

.. confval:: target_port

    :type: int
    :required: true

    The port SSH runs on (on the remote server). Defaults to 22.

.. confval:: ssh_username

    :type: string
    :required: true

    Login username.

.. confval:: ssh_private_key_path

    :type: string
    :required: true

    The absolute path to the OpenSSH *private* key to login on the remote server. The remote server must have a corresponding entry in ``authorized_keys`` for the user that connects.

.. confval:: command

    :type: string
    :required: true

    The command to run. It will use the context of the logged-in user and it is recommended to use absolute pathnames for commands. It is best to test the command by logging in as ``ssh_username`` and trying the command at the prompt.

.. confval:: regex

    :type: string
    :required: true

    The regular expression the output of the command above will be matched to.

    * Make sure to have one matching group - this is the value that will be checked
    * Do not escape the sequences (i.e. use ``\s`` in the configuration when you mean "whitespace")
    * A fantastic site to check your regex is https://regex101.com (do not block their ads!)

.. confval:: result_type

    :type: string
    :required: true

    The type of the extracted value. Can be ``str`` (a string) or ``int`` (a number)

.. confval:: target_value

    :type: string
    :required: true

    The value to compare extracted results with. Must be of the same type as the extracted value.

.. confval:: operator

    :type: string
    :required: true

    The operator that compares the extracted value with ``target_value``. The possible operators are:

    * ``equals`` - works with numbers and strings
    * ``not_equals`` - works with number and strings
    * ``greater_than`` - works with numbers
    * ``less_than`` - works with numbers

.. confval:: success_message

    :type: string
    :required: false

    A templated message for monitoring success. It must be a string `compatible with ``.format()`` https://docs.python.org/3/tutorial/inputoutput.html#the-string-format-method`_. You can use one bracket (``{}``) which will be replaced with the extracted value.

An example of a full configuration that checks if the ``/dev/sda`` disk on machine ``srv.example.com`:2255`` has more that 10% of free space available:

.. code-block::

    [srv]
    type = remote_ssh
    description=check disk space on srv
    command = df -k | grep /dev/sda
    ssh_private_key_path = C:\Users\mark\.ssh\srv.private.openssh
    ssh_username = root
    target_hostname = srv.example.com
    target_port = 2255
    regex = .*\s(\d+)%
    operator = greater_than
    target_value = 10
    result_type = int
    success_message=free disk {}%
