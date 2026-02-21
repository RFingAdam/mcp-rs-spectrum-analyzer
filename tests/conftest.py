"""Pytest configuration and fixtures."""

import asyncio
import os
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_scpi_socket():
    """Create mock SCPI socket."""
    socket = AsyncMock()
    socket.is_connected = True
    socket.address = "192.168.1.100:5025"

    # Default responses
    socket.query = AsyncMock(return_value="Rohde&Schwarz,FSW-26,1312.8000K26/100001,4.30.018.28")
    socket.send = AsyncMock()
    socket.wait_opc = AsyncMock(return_value=True)
    socket.query_float_list = AsyncMock(return_value=[-80.0, -75.0, -70.0, -65.0, -60.0])

    return socket


@pytest.fixture
def sa_test_config():
    """Get spectrum analyzer test configuration from environment."""
    return {
        "host": os.environ.get("SA_TEST_HOST", "192.168.1.100"),
        "port": int(os.environ.get("SA_TEST_PORT", "5025")),
    }


@pytest.fixture
def skip_without_sa(sa_test_config):
    """Skip test if no spectrum analyzer available."""
    if not os.environ.get("SA_TEST_HOST"):
        pytest.skip("SA_TEST_HOST not set, skipping integration test")
