"""Shared connection management for tool handlers.

Backed by :class:`scpi_core.ConnectionRegistry` instead of a module-global dict
plus a hand-rolled lock. The dict had no expiry, so a connection opened by one
tool call stayed open until the process died; the registry gives it an idle TTL
and a single eviction path.

What is cached is the *driver*, not the transport, which is what the old dict
held too. The registry only ever asks its entries for ``is_connected``,
``connect()`` and ``disconnect()``, and ``RSSpectrumAnalyzerDriver`` provides all
three with the same meanings -- so caching the driver keeps the analyzer's
connection state and its transport's connection state from drifting apart, which
two parallel caches would not.
"""

import logging
from typing import cast

from scpi_core import ConnectionRegistry, SCPITransport

from ..config import get_settings
from ..driver import RSSpectrumAnalyzerDriver
from ..transport import create_transport

logger = logging.getLogger(__name__)


async def _teardown_sa(key: str, handle: SCPITransport) -> None:
    """Evict hook: the one place a connection's end is accounted for.

    A spectrum analyzer is receive-only, so unlike a generator or a test set
    there is no output to switch off here -- dropping the socket *is* the safe
    state. The registry closes the handle itself immediately after this hook by
    calling the same ``disconnect()`` that ``sa_disconnect`` calls, so eviction
    and explicit disconnect really do run one teardown path and this hook must
    not duplicate it.

    What it does add is the resync tally. Repeated resyncs mean command timeouts
    were set tighter than the sweep times actually in use, and that evidence
    lives on the transport -- it would vanish with the handle unless something
    reads it on the way out.
    """
    sa = cast(RSSpectrumAnalyzerDriver, handle)
    resyncs = sa.resync_count
    if resyncs:
        logger.warning(
            "Closing %s after %d stream resync(s); command timeouts are likely "
            "tighter than the configured sweep time",
            key,
            resyncs,
        )
    else:
        logger.info("Closing spectrum analyzer connection %s", key)


#: Live analyzer connections. Idle TTL is the registry default: an analyzer left
#: untouched for a quarter of an hour is almost certainly a finished measurement,
#: and holding its socket blocks the next operator at the bench.
_sa_registry = ConnectionRegistry(on_evict=_teardown_sa)


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

    async def connect() -> SCPITransport:
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
        return cast(SCPITransport, sa)

    return cast(RSSpectrumAnalyzerDriver, await _sa_registry.acquire(key, connect))


async def _close_sa(host: str, port: int) -> bool:
    """Close spectrum analyzer connection."""
    key = _get_connection_key(host, port)
    if key not in _sa_registry.keys():
        return False
    await _sa_registry.release(key)
    return True
