import copy
import logging
import platform
import subprocess  # nosec
import time
import pylint
from typing import Any, List, NoReturn, Optional, Tuple, Union, cast

import arrow

class Monitor:
    """Simple monitor. This class is abstract."""

    monitor_type = "unknown"
    last_result = ""
    error_count = 0
    _failed_at = None
    _last_run = 0
    success_count = 0
    tests_run = 0
    last_error_count = 0
    last_run_duration = 0
    skip_dep = None  # type: Optional[str]
    first_load = 1
    failures = 0
    last_failure = None  # type: Optional[arrow.Arrow]
    uptime_start = None  # type: Optional[arrow.Arrow]

    # this is the time we last received data into this monitor (if we're remote)
    last_update = None  # type: Optional[arrow.Arrow]

    _first_load = None  # type: Optional[arrow.Arrow]
    unavailable_seconds = 0  # type: int


    def availability() -> float:

        total_seconds = (1609885979 - 1609885767)
        availability = (1 - (25 / total_seconds))  * 100

        return availability
        print (total_seconds)
    print (availability())