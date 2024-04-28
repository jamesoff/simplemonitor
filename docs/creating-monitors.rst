Creating Monitors
=================

To create your own Monitor, you need to:

1. Create a Python file in :file:`simplemonitor/Monitors` (or pick a suitable existing one to add it to)
2. If you're creating a new file, you'll need a couple of imports:

.. code-block:: python

   from .monitor import Monitor, register

3. Define your monitor class, which should subclass ``Monitor`` and be decorated by ``@register``. Set a class attribute for the "type" which will be used in the monitor configuration to use it.

.. code-block:: python

    @register
    class MonitorMyThing(Monitor):

        monitor_type = "my_thing"

4. Define your initialiser. It should call the superclass's initialiser, and then read its configuration values from the supplied dict. You can also do any other initialisation here.

   This code should be safe to re-run, as if SimpleMonitor reloads its configuration, it will call ``__init__()`` with the new configuration dict. Use the :py:func:`get_config_option` helper to read config values.

.. code-block:: python

    @register
    class MonitorMyThing(Monitor):

        monitor_type = "my_thing"

        def __init__(self, name: str, config_options: dict) -> None:
            super().__init__(name, config_options)
            self.my_setting = self.get_config_option("my_setting", required=True)

5. Add a ``run_test`` function. This should perform the test for your monitor, and call ``record_fail()`` or ``record_success()`` as appropriate. It must also return ``False`` or ``True`` to match. The two ``record_*()`` methods return the right value, so you can just use them as the value to ``return``. You can use ``self.monitor_logger`` to perform logging (it's a standard Python :py:mod:`logging` object).

   You should catch any suitable exceptions and handle them as a failure of the monitor. The main loop will handle any uncaught exceptions and fail the monitor with a generic message.

.. code-block:: python

    @register
    class MonitorMyThing(Monitor):

        # ...

        def run_test(self) -> bool:
            # my test logic here
            if test_succeeded:
                return self.record_success("it worked")
            return self.record_fail(f"failed with message {test_result}")

6. You should also give a ``describe`` function, which explains what this monitor is checking for:

.. code-block:: python

    @register
    class MonitorMyThing(Monitor):

        # ...

        def describe(self) -> str:
            return f"checking that thing f{my_setting} does foo"

7. You should also provide a ``get_params()`` method that sends back a tuple of the configuration entries of your Monitor. It will be used by Loggers as an input of which information to log.

.. code-block:: python

    @register
    class MonitorMyThing(Monitor):

        def __init__(self, name: str, config_options: dict) -> None:
            super().__init__(name, config_options)
            self.some_configuration = cast(str, self.get_config_option("some_configuration"))
            self.some_other_configuration = cast(str, self.get_config_option("some_other_configuration"))

        # ...
         
        def get_params(self) -> Tuple:
            return (
                self.some_configuration,
                self.some_other_configuration,
            )

8. In :file:`simplemonitor/Monitors/__init__.py`, add your Monitor to the list of imports.

That's it! You should now be able to use ``type=my_thing`` in your Monitors configuration to use your monitor.

If you'd like to share your monitor back via a PR, please also:

1. Use type decorators, and verify with `mypy <https://mypy.readthedocs.io/en/stable/>`_. You may need to use ``cast(TYPE, self.get_config_option(...))`` in your ``__init__()`` to get things to settle down. See existing monitors for examples.
2. Use `Black <https://pre-commit.com/>`_ to format the code.
3. Add documentation for your monitor. Create a file in `docs/monitors/` called `my_thing.rst` and follow the pattern in the other files to document it.

There's a `pre-commit <https://pre-commit.com/>`_ configuration in the repo which you can use to check things over.
