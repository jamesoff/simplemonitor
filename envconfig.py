import os
import re

from ConfigParser import ConfigParser

class EnvironmentAwareConfigParser(ConfigParser):
    """A subclass of ConfigParser which allows %env:VAR% interpolation via the
    get method."""

    r = re.compile('%env:([a-zA-Z0-9_]+)%')

    def read(self, filenames):
        result = ConfigParser.read(self, filenames)
        for section in self.sections():
            original_section = section
            matches = self.r.search(section)
            while matches:
                env_key = matches.group(1)
                if env_key in os.environ:
                    section = section.replace(matches.group(0), os.environ[env_key])
                matches = self.r.search(section)
            if section != original_section:
                self.add_section(section)
                for (option, value) in self.items(original_section):
                    self.set(section, option, value)
                self.remove_section(original_section)
        return result


    def get(self, *args, **kwargs):
        result = ConfigParser.get(self, *args, **kwargs)
        matches = self.r.search(result)
        while matches:
            env_key = matches.group(1)
            if env_key in os.environ:
                result = result.replace(matches.group(0), os.environ[env_key])
            matches = self.r.search(result)
        return result


