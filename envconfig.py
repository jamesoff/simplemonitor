import os
import re

import sys
if sys.version_info[0] == 2:
    from ConfigParser import ConfigParser
else:
    from configparser import ConfigParser
    from configparser import BasicInterpolation


class EnvironmentAwareConfigParser(ConfigParser):
    """A subclass of ConfigParser which allows %env:VAR% interpolation via the
    get method."""

    r = re.compile('%env:([a-zA-Z0-9_]+)%')

    def __init__(self, *args, **kwargs):
        """Init with our specific interpolation class (for Python 3)"""
        try:
            interpolation = EnvironmentAwareInterpolation()
            kwargs['interpolation'] = interpolation
        except:
            # Python 2
            pass
        ConfigParser.__init__(self, *args, **kwargs)

    def read(self, filenames):
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
                    raise ValueError('Cannot find {} in environment for config interpolation'.format(env_key))

                matches = self.r.search(section)
            if section != original_section:
                self.add_section(section)
                for (option, value) in self.items(original_section):
                    self.set(section, option, value)
                self.remove_section(original_section)
        return result

    def get(self, *args, **kwargs):
        if sys.version_info[0] > 2:
            return ConfigParser.get(self, *args, **kwargs)
        result = ConfigParser.get(self, *args, **kwargs)
        matches = self.r.search(result)
        while matches:
            env_key = matches.group(1)
            if env_key in os.environ:
                result = result.replace(matches.group(0), os.environ[env_key])
            matches = self.r.match(result)
        return result

if sys.version_info[0] > 2:
    class EnvironmentAwareInterpolation(BasicInterpolation):
        r = re.compile('%env:([a-zA-Z0-9_]+)%')

        def before_get(self, parser, section, option, value, defaults):
            parser.get(section, option, raw=True, fallback=value)
            matches = self.r.search(value)
            old_value = value
            while matches:
                env_key = matches.group(1)
                if env_key in os.environ:
                    value = value.replace(matches.group(0), os.environ[env_key])
                else:
                    raise ValueError('Cannot find {} in environment for config interpolation'.format(env_key))
                matches = self.r.search(value)
                if value == old_value:
                    break
                old_value = value
            return value

