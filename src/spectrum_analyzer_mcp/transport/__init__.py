"""SCPI transport layer abstraction.

Provides pluggable transports for communicating with instruments:
- TCPSocketTransport: Direct TCP/IP socket (default, no extra deps)
- VISATransport: VISA resources via pyvisa (optional, supports GPIB/USB/HiSLIP)
"""

from .base import SCPITransport
from .factory import create_transport
from .tcp_socket import TCPSocketTransport

__all__ = [
    "SCPITransport",
    "TCPSocketTransport",
    "create_transport",
]
