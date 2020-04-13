import datetime
import json
import re
from typing import Any

import arrow

from . import MonitorState

DATETIME_MAGIC_TOKEN = "__simplemonitor_datetime"  # nosec
MONITORSTATE_MAGIC_TOKEN = "__simplemonitor_monitorstate"  # nosec
ARROW_MAGIC_TOKEN = "__simplemonitor_arrow"  # nosec
FORMAT = "%Y-%m-%d %H:%M:%S.%f"


class JSONEncoder(json.JSONEncoder):
    _regexp_type = type(re.compile(""))

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime.datetime):
            return {DATETIME_MAGIC_TOKEN: obj.strftime(FORMAT)}
        if isinstance(obj, self._regexp_type):
            return "<removed compiled regexp object>"
        if isinstance(obj, MonitorState):
            return {MONITORSTATE_MAGIC_TOKEN: obj.name}
        if isinstance(obj, arrow.Arrow):
            return {ARROW_MAGIC_TOKEN: obj.for_json()}
        return super(JSONEncoder, self).default(obj)


class JSONDecoder(json.JSONDecoder):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._original_object_pairs_hook = kwargs.pop("object_pairs_hook", None)
        kwargs["object_pairs_hook"] = self.object_pairs_hook
        super(JSONDecoder, self).__init__(*args, **kwargs)

    _datetime_re = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}")

    def object_pairs_hook(self, obj: Any) -> Any:
        if (
            len(obj) == 1
            and obj[0][0] == DATETIME_MAGIC_TOKEN
            and isinstance(obj[0][1], str)
            and self._datetime_re.match(obj[0][1])
        ):
            return datetime.datetime.strptime(obj[0][1], FORMAT)
        elif (
            len(obj) == 1
            and obj[0][0] == MONITORSTATE_MAGIC_TOKEN
            and isinstance(obj[0][1], str)
        ):
            return MonitorState[obj[0][1]]
        elif (
            len(obj) == 1
            and obj[0][0] == ARROW_MAGIC_TOKEN
            and isinstance(obj[0][1], str)
        ):
            return arrow.get(obj[0][1])
        elif self._original_object_pairs_hook:
            return self._original_object_pairs_hook(obj)
        else:
            return dict(obj)


def json_dumps(data: Any) -> bytes:
    return JSONEncoder().encode(data).encode("ascii")


def json_loads(string: bytes) -> str:
    return JSONDecoder().decode(string.decode("ascii"))
