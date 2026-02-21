"""Transport factory for creating appropriate SCPI transports."""

import logging

from .base import SCPITransport
from .tcp_socket import TCPSocketTransport

logger = logging.getLogger(__name__)

# VISA resource string prefixes
_VISA_PREFIXES = ("TCPIP::", "GPIB::", "USB::", "ASRL::", "VXI::", "PXI::")


def create_transport(
    *,
    host: str | None = None,
    port: int | None = None,
    resource: str | None = None,
    timeout: float = 5.0,
    command_timeout: float = 30.0,
) -> SCPITransport:
    """Create appropriate transport from connection parameters.

    Args:
        host: Hostname or IP for TCP socket connections.
        port: TCP port (default 5025).
        resource: VISA resource string (e.g. ``TCPIP::192.168.1.100::INSTR``).
            When provided, host/port are ignored and VISATransport is used.
        timeout: Connection timeout in seconds.
        command_timeout: Command timeout in seconds.

    Returns:
        Configured SCPITransport instance (not yet connected).

    Raises:
        ValueError: If neither host nor resource is provided.
        ImportError: If resource is a VISA string but pyvisa is not installed.
    """
    if resource is not None:
        return _create_visa_transport(resource, timeout, command_timeout)

    if host is not None:
        return TCPSocketTransport(
            host=host,
            port=port or TCPSocketTransport.DEFAULT_PORT,
            timeout=timeout,
            command_timeout=command_timeout,
        )

    raise ValueError("Either 'host' or 'resource' must be provided to create a transport")


def _create_visa_transport(resource: str, timeout: float, command_timeout: float) -> SCPITransport:
    """Create VISA transport, falling back to TCP if it's a simple SOCKET resource."""
    # Check if this looks like a VISA string
    resource_upper = resource.upper()

    if not any(resource_upper.startswith(p) for p in _VISA_PREFIXES):
        raise ValueError(
            f"Unrecognised resource string: {resource!r}. "
            f"Expected VISA format (e.g. TCPIP::192.168.1.100::INSTR) "
            f"or use host/port for direct TCP."
        )

    # Try to use VISA transport
    try:
        from .visa import VISATransport

        return VISATransport(
            resource_string=resource,
            timeout=timeout,
            command_timeout=command_timeout,
        )
    except ImportError:
        # If it's a TCPIP SOCKET resource, we can fall back to raw TCP
        if "SOCKET" in resource_upper and resource_upper.startswith("TCPIP::"):
            host, port = _parse_tcpip_socket_resource(resource)
            logger.info(
                "pyvisa not installed; falling back to TCP socket for %s",
                resource,
            )
            return TCPSocketTransport(
                host=host,
                port=port,
                timeout=timeout,
                command_timeout=command_timeout,
            )
        raise ImportError(
            f"pyvisa is required for resource {resource!r}. "
            "Install with: pip install spectrum-analyzer-mcp[visa]"
        )


def _parse_tcpip_socket_resource(resource: str) -> tuple[str, int]:
    """Parse host and port from a TCPIP SOCKET resource string.

    Format: ``TCPIP::<host>::<port>::SOCKET``
    """
    parts = resource.split("::")
    if len(parts) < 4:
        raise ValueError(f"Invalid TCPIP SOCKET resource: {resource!r}")

    host = parts[1]
    try:
        port = int(parts[2])
    except ValueError:
        raise ValueError(f"Invalid port in TCPIP SOCKET resource: {resource!r}")

    return host, port
