"""A version of ConfigParser which supports subsitutions from environment variables."""

import os
import re
from configparser import BasicInterpolation, ConfigParser
from typing import Any, List, Optional


class EnvironmentAwareConfigParser(ConfigParser):
    """A subclass of ConfigParser which allows %env:VAR% interpolation via the
    get method."""

    r = re.compile("%env:([a-zA-Z0-9_]+)%")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init with our specific interpolation class (for Python 3)"""
        interpolation = EnvironmentAwareInterpolation()
        kwargs["interpolation"] = interpolation
        ConfigParser.__init__(self, *args, **kwargs)

    def read(self, filenames: Any, encoding: Optional[str] = None) -> List[str]:
        """Load a config file and do environment variable interpolation on the section names."""
        result = ConfigParser.read(self, filenames)
        for section in self.sections():
            original_section = section
            matches = self.r.search(section)
            while matches:
                env_key = matches.group(1)
                if env_key in os.environ:
                    section = section.replace(matches.group(0), os.environ[env_key])
                else:
                    raise ValueError(
                        "Cannot find {0} in environment for config interpolation".format(
                            env_key
                        )
                    )

                matches = self.r.search(section)
            if section != original_section:
                self.add_section(section)
                for option, value in self.items(original_section):
                    self.set(section, option, value)
                self.remove_section(original_section)
        return result


class EnvironmentAwareInterpolation(BasicInterpolation):
    """An interpolation which substitutes values from the environment."""

    r = re.compile("%env:([a-zA-Z0-9_]+)%")

    def before_get(
        self, parser: Any, section: str, option: str, value: Any, defaults: Any
    ) -> Any:
        parser.get(section, option, raw=True, fallback=value)
        matches = self.r.search(value)
        old_value = value
        while matches:
            env_key = matches.group(1)
            if env_key in os.environ:
                value = value.replace(matches.group(0), os.environ[env_key])
            else:
                raise ValueError(
                    "Cannot find {0} in environment for config interpolation".format(
                        env_key
                    )
                )
            matches = self.r.search(value)
            if value == old_value:
                break
            old_value = value
        return value
