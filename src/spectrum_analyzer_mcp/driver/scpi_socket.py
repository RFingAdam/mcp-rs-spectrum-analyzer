"""Backward-compatible import path for the raw-socket transport.

``SCPISocket`` used to be a local alias here; it is now the real class name in
``scpi_core.transport``. New code should import from
``spectrum_analyzer_mcp.transport``.
"""

from ..transport import SCPISocket

__all__ = ["SCPISocket"]
