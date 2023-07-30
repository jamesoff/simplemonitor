"""
Monitors for SimpleMonitor
"""

from .arlo import MonitorArloCamera
from .compound import CompoundMonitor
from .file import MonitorBackup
from .hass import MonitorSensor
from .host import (
    MonitorApcupsd,
    MonitorCommand,
    MonitorDiskSpace,
    MonitorFileStat,
    MonitorLoadAvg,
    MonitorMemory,
    MonitorPkgAudit,
    MonitorPortAudit,
    MonitorSwap,
    MonitorZap,
)
from .network import (
    MonitorDNS,
    MonitorHost,
    MonitorHTTP,
    MonitorPing,
    MonitorTCP,
    MonitorTLSCert,
)
from .ring import MonitorRingDoorbell
from .service import (
    MonitorEximQueue,
    MonitorProcess,
    MonitorRC,
    MonitorService,
    MonitorSvc,
    MonitorSystemdUnit,
    MonitorUnixService,
    MonitorWindowsDHCPScope,
)
from .unifi import MonitorUnifiFailover, MonitorUnifiFailoverWatchdog

__all__ = [
    "CompoundMonitor",
    "MonitorApcupsd",
    "MonitorArloCamera",
    "MonitorBackup",
    "MonitorCommand",
    "MonitorDNS",
    "MonitorDiskSpace",
    "MonitorEximQueue",
    "MonitorFileStat",
    "MonitorHTTP",
    "MonitorHost",
    "MonitorLoadAvg",
    "MonitorMemory",
    "MonitorPing",
    "MonitorPkgAudit",
    "MonitorPortAudit",
    "MonitorProcess",
    "MonitorRC",
    "MonitorRingDoorbell",
    "MonitorSensor",
    "MonitorService",
    "MonitorSvc",
    "MonitorSwap",
    "MonitorSystemdUnit",
    "MonitorTCP",
    "MonitorTLSCert",
    "MonitorUnifiFailover",
    "MonitorUnifiFailoverWatchdog",
    "MonitorUnixService",
    "MonitorWindowsDHCPScope",
    "MonitorZap",
]
