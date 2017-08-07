import os
import re

from ConfigParser import ConfigParser

class EnvironmentAwareConfigParser(ConfigParser):
    """A subclass of ConfigParser which allows %env:VAR% interpolation via the
    get method."""

    r = re.compile('%env:([a-zA-Z0-9_]+)%')

    def get(self, *args, **kwargs):
        result = ConfigParser.get(self, *args, **kwargs)
        matches = self.r.search(result)
        while matches:
            env_key = matches.group(1)
            if env_key in os.environ:
                result = result.replace(matches.group(0), os.environ[env_key])
            matches = self.r.match(result)
        return result


