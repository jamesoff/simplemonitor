slack - Slack webhook
^^^^^^^^^^^^^^^^^^^^^

.. warning:: Do not commit your credentials to a public repo!

First, set up a webhook for this to use.

* Go to https://slack.com/apps/manage
* Add a new webhook
* Configure it to taste (channel, name, icon)
* Copy the webhook URL for your configuration below

.. confval:: url

    :type: string
    :required: true

    the Slack webhook URL

.. confval:: channel

    :type: string
    :required: false
    :default: the channel configured on the webhook

    the channel to send to

.. confval:: username

    :type: string
    :required: false
    :default: a username to send to

.. confval:: timeout

    :type: int
    :required: false
    :default: ``5``

    Timeout for HTTP request to Slack
