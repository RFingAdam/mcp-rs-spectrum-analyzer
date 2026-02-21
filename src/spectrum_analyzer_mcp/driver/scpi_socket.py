"""Async TCP/IP SCPI transport (backward-compatible wrapper).

This module re-exports ``TCPSocketTransport`` as ``SCPISocket`` for
backward compatibility. New code should import from
``spectrum_analyzer_mcp.transport`` instead.
"""

from ..transport.tcp_socket import TCPSocketTransport

# Backward-compatible alias
SCPISocket = TCPSocketTransport

__all__ = ["SCPISocket"]
