mqtt_client - monitor a mqtt topic
^^^^^^^^^^^^^^^^^^

Subscipe to a MQTT topic and compare the payload with a success state

.. confval:: broker

   :type: string
   :required: true

   the hostname or IP of the broker

.. confval:: port

    :type: int
    :required: false
    :default: ``1883``

    The port of the broker

.. confval:: tls

    :type: bool
    :required: false
    :default: ``false``

    Use tls

.. confval:: ca_cert

    :type: string
    :required: false
    :default: ````

    Path to the CA cert. Otherwise, use the system CAs

.. confval:: topic

    :type: string
    :required: true
    :default: ````

    The topic which simplemonitor will subscribe to

.. confval:: success_state

    :type: string
    :required: true
    :default: ````

    The success state of the payload. Can be a Number, a string or a comparison (e.g. <10,>10,0<x<10)