"""Abstract base class for SCPI transports."""

from abc import ABC, abstractmethod


class SCPITransport(ABC):
    """Abstract SCPI transport interface.

    All transports (TCP socket, VISA, GPIB, USB, HiSLIP) implement this
    interface so the driver layer is decoupled from the communication method.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to instrument."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to instrument."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected."""

    @property
    @abstractmethod
    def address(self) -> str:
        """Return human-readable address string for logging/errors."""

    @abstractmethod
    async def send(self, command: str) -> None:
        """Send SCPI command without waiting for response."""

    @abstractmethod
    async def query(self, command: str, timeout: float | None = None) -> str:
        """Send query and return response string."""

    @abstractmethod
    async def query_binary(self, command: str, timeout: float | None = None) -> bytes:
        """Send query and return binary response."""

    @abstractmethod
    async def query_float_list(self, command: str, timeout: float | None = None) -> list[float]:
        """Query and parse comma-separated float values."""

    @abstractmethod
    async def wait_opc(self, timeout: float | None = None) -> bool:
        """Wait for operation complete (*OPC?)."""

    async def __aenter__(self) -> "SCPITransport":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
