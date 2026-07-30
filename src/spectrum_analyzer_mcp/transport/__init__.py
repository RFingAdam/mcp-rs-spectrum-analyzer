"""SCPI transport layer -- re-export shim over :mod:`scpi_core.transport`.

The abstraction that used to live here (``SCPITransport``, ``VISATransport``,
``create_transport``) was moved into ``scpi-core`` so the three R&S servers stop
carrying diverged copies of it. The raw-socket implementation was not moved: it
was *replaced*. ``TCPSocketTransport`` took its send and its matching read under
two separate awaits with no lock spanning both and no notion of a poisoned
stream, so after a read timeout it happily returned the previous query's answer
to the next caller -- a wrong measurement with no error anywhere.
``scpi_core.SCPISocket`` holds the pair under one transaction and marks the
connection desynced until it is proven clean again.

Every name that was importable from this module still is, so existing
``from ..transport import ...`` sites keep working.
"""

from scpi_core.transport import (
    PYVISA_AVAILABLE,
    Idempotency,
    SCPISocket,
    SCPITransport,
    VISATransport,
    create_transport,
)

#: ``TCPSocketTransport`` was this package's raw-socket transport. It is gone;
#: ``SCPISocket`` supersedes it with the same constructor signature
#: ``(host, port, timeout, command_timeout)``. The alias stays so third-party
#: code and older docs that name the old class still resolve to a working
#: transport -- one that additionally detects desync.
TCPSocketTransport = SCPISocket

__all__ = [
    "PYVISA_AVAILABLE",
    "Idempotency",
    "SCPISocket",
    "SCPITransport",
    "TCPSocketTransport",
    "VISATransport",
    "create_transport",
]
