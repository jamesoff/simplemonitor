Creating Alerters
=================

To create your own Alerter, you need to:

1. Create a Python file in :file:`simplemonitor/Alerters` (or pick a suitable existing one to add it to)
2. If you're creating a new file, you'll need a couple of imports:

    .. code-block:: python

       from ..Monitors.monitor import Monitor
       from .alerter import Alerter, AlertLength, AlertType, register

3. Define your alerter class, which should subclass ``Alerter`` and be decorated by ``@register``. Set a class attribute for the "type" which will be used in the alerter configuration to use it.

    .. code-block:: python

        @register
        class MyAlerter(Alerter):

            alerter_type = "my_alerter"

4. Define your initialiser. It should call the superclass's initialiser, and then read its configuration values from the supplied dict. You can also do any other initialisation here.

   This code should be safe to re-run, as if SimpleMonitor reloads its configuration, it will call ``__init__()`` with the new configuration dict. Use the :py:func:`get_config_option` helper to read config values.

    .. code-block:: python

        @register
        class MyAlerter(Alerter):

            alerter_type = "my_alerter"

            def __init__(self, config_options: dict) -> None:
                super().__init__(config_options)
                self.my_setting = self.get_config_option("setting", required=True)

5. Add a ``send_alerter`` function. This receives the information for a single monitor. You should first call ``self.should_alert(monitor)``, which will return the type of alert to be sent (e.g. failure). You should return if it is ``AlertType.NONE``.

   You should then prepare your message. Call ``self.build_message()`` to generate the message content. Check the value of ``self._dry_run`` and if it is True, you should log (using ``self.alerter_logger.info(...)``) what you would do, else you should do it.

   .. py:function:: Alerter.build_message(length: AlertLength, alert_type: AlertType, monitor: Monitor) -> str

    Generate a suitable length alert message for the given type of alert, for the given Monitor.

    :param AlertLength: one of the AlertLength enum values: ``NOTIFICATION`` (shortest), ``SMS`` (will be <= 140 chars), ``ONELINE``, ``TERSE`` (not currently supported), ``FULL``, or ``ESSAY``
    :param AlertType: one of the AlertType enum values: ``NONE``, ``FAILURE``, ``CATCHUP``, or ``SUCCESS``
    :param monitor: the Monitor to generate the message for
    :return: the built message
    :rtype: str
    :raises ValueError: if the AlertType is unknown
    :raises NotImplementedError: if the AlertLength is unknown or unsupported

7. You should also give a ``_describe_action`` function, which explains what this alerter does. Note that the time configuration for the alerter will be automatically added:

    .. code-block:: python

        @register
        class MyAlerter(Alerter):

            # ...

            def _describe_action(self) -> str:
                return f"sending FooAlerters to {self.recipient}"

7. In :file:`simplemonitor/Alerters/__init__.py`, add your Alerter to the list of imports.

That's it! You should now be able to use ``type=my_alerter`` in your Alerters configuration to use your alerter.
