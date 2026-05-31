"""
Monitors for SimpleMonitor
"""

from .apcupssnmp import MonitorAPCUPSSNMP
from .arlo import MonitorArloCamera
from .compound import CompoundMonitor, RemoteHostsMonitor
from .file import MonitorBackup
from .gmirror import MonitorGmirrorStatus
from .hass import MonitorSensor
from .host import (
    MonitorApcupsd,
    MonitorCommand,
    MonitorDiskSpace,
    MonitorFileStat,
    MonitorLoadAvg,
    MonitorMemory,
    MonitorNUT,
    MonitorPkgAudit,
    MonitorPortAudit,
    MonitorSwap,
    MonitorZap,
    MonitorZpool,
)
from .mqtt import MonitorMQTT
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
    "MonitorAPCUPSSNMP",
    "MonitorMQTT",
    "CompoundMonitor",
    "MonitorApcupsd",
    "MonitorArloCamera",
    "MonitorBackup",
    "MonitorCommand",
    "MonitorDNS",
    "MonitorDiskSpace",
    "MonitorEximQueue",
    "MonitorFileStat",
    "MonitorGmirrorStatus",
    "MonitorHTTP",
    "MonitorHost",
    "MonitorLoadAvg",
    "MonitorMemory",
    "MonitorNUT",
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
    "MonitorZpool",
    "RemoteHostsMonitor",
]
