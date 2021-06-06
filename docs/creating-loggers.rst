Creating Loggers
================

Before writing your logger, you need to consider if you should support **batching** or not. If a logger supports batching, then it collects all the monitor results and then performs its logging action. For example, the HTML logger uses batching so that when it generates the HTML output, it knows all the monitors to include (and can sort them etc). Non-batching loggers will simply perform their logging action multiple times, once per monitor.

To create your own Logger, you need to:

1. Create a Python file in :file:`simplemonitor/Loggers` (or pick a suitable existing one to add it to)
2. If you're creating a new file, you'll need a couple of imports:

    .. code-block:: python

       from ..Monitors.monitor import Monitor
       from .logger import Logger, register

3. Define your logger class, which should subclass ``Logger`` and be decorated by ``@register``. Set a class attribute for the "type" which will be used in the logger configuration to use it. Additionally, set the ``supports_batch`` value to indicate if your logger should be used in batching mode.

    .. code-block:: python

        @register
        class MyLogger(Logger):

            logger_type = "my_logger"
            supports_batch = True  # or False

4. Define your initialiser. It should call the superclass's initialiser, and then read its configuration values from the supplied dict. You can also do any other initialisation here.

   This code should be safe to re-run, as if SimpleMonitor reloads its configuration, it will call ``__init__()`` with the new configuration dict. Use the :py:func:`get_config_option` helper to read config values.

    .. code-block:: python

        @register
        class MyLogger(Logger):

            logger_type = "my_logger"

            def __init__(self, config_options: dict) -> None:
                super().__init__(config_options)
                self.my_setting = self.get_config_option("setting", required=True)

5. Add a ``save_result2`` function (yes, I know). This receives the information for a single monitor.

   **Batching loggers** should save the information they need to into `self.batch_data`, which should (but does not have to be) a dict of `str: Any` using the monitor name as the key. This is automatically initialised to an empty dict at the start of the batch. You should extend the `start_batch` method from `Logger` to customise it.

    .. code-block:: python

        @register
        class MyLogger(Logger):

            # ...

            def save_result2(self, name: str, monitor: Monitor) -> None:
                self.batch_data[name] = monitor.state

   **Non-batching loggers** can perform whatever logging action they are designed for at this point.

   .. code-block:: python

        @register
        class MyLogger(Logger):

            # ...

            def save_result2(self, name: str, monitor: Monitor) -> None:
                self._my_logger_action(f"Monitor {name} is in state {monitor.state}")

6. **Batching loggers** only should provide a ``process_batch`` method, which is called after all the monitors have been processed. This is where you should perform your batched logging operation.

   .. code-block:: python

        @register
        class MyLogger(Logger):

            # ...

            def process_batch(self) -> None:
                with open(self.filename, "w") as file_handle:
                    for monitor, state in self.batch_data.iteritems():
                    file_handle.write(f"Monitor {monitor} is in state {state}\n")

7. You should also give a ``describe`` function, which explains what this logger does:

    .. code-block:: python

        @register
        class MyLogger(Logger):

            # ...

            def describe(self) -> str:
                return f"writing monitor info to {self.filename}"

7. In :file:`simplemonitor/Loggers/__init__.py`, add your Logger to the list of imports.

That's it! You should now be able to use ``type=my_thing`` in your Loggers configuration to use your logger.
