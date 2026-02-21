"""Shared connection management for tool handlers."""

import asyncio
import logging

from ..config import get_settings
from ..driver import RSSpectrumAnalyzerDriver
from ..transport import create_transport

logger = logging.getLogger(__name__)

# Global connection manager
_sa_connections: dict[str, RSSpectrumAnalyzerDriver] = {}

# asyncio.Lock for shared mutable state
_connection_lock = asyncio.Lock()


def _get_connection_key(host: str, port: int) -> str:
    """Generate unique key for connection."""
    return f"{host}:{port}"


async def _get_sa(
    host: str | None = None,
    port: int | None = None,
    resource: str | None = None,
) -> RSSpectrumAnalyzerDriver:
    """Get or create spectrum analyzer connection.

    Args:
        host: Hostname or IP. Falls back to settings default.
        port: TCP port. Falls back to settings default.
        resource: VISA resource string. Overrides host/port when provided.
    """
    settings = get_settings()
    resource = resource or settings.resource_string
    host = host if host is not None else settings.default_host
    port = port if port is not None else settings.default_port
    key = resource if resource else _get_connection_key(host, port)

    async with _connection_lock:
        if key in _sa_connections:
            sa = _sa_connections[key]
            if sa.is_connected:
                return sa

        # Create transport and driver
        transport = create_transport(
            host=host if not resource else None,
            port=port if not resource else None,
            resource=resource,
            timeout=settings.connection_timeout,
            command_timeout=settings.command_timeout,
        )
        sa = RSSpectrumAnalyzerDriver(
            host=host,
            port=port,
            timeout=settings.connection_timeout,
            command_timeout=settings.command_timeout,
            safety_limits=settings.get_safety_limits(),
            transport=transport,
        )
        await sa.connect()
        _sa_connections[key] = sa
        return sa


async def _close_sa(host: str, port: int) -> bool:
    """Close spectrum analyzer connection."""
    key = _get_connection_key(host, port)
    async with _connection_lock:
        if key in _sa_connections:
            sa = _sa_connections.pop(key)
            await sa.disconnect()
            return True
        return False
