"""Async TCP/IP socket transport for SCPI instruments."""

import asyncio
import logging

from ..exceptions import CommunicationError, ConnectionError, TimeoutError
from .base import SCPITransport

logger = logging.getLogger(__name__)


class TCPSocketTransport(SCPITransport):
    """TCP/IP socket transport for SCPI commands.

    Direct async TCP socket connection, typically on port 5025 (R&S, Siglent)
    or 5555 (Rigol). No external dependencies required.

    Example::

        async with TCPSocketTransport("192.168.1.100", 5025) as scpi:
            idn = await scpi.query("*IDN?")
    """

    DEFAULT_PORT = 5025
    TERMINATOR = "\n"
    BUFFER_SIZE = 65536

    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = DEFAULT_PORT,
        timeout: float = 5.0,
        command_timeout: float = 30.0,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.command_timeout = command_timeout

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._writer is not None

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    async def connect(self) -> None:
        if self._connected:
            return

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            self._connected = True
            logger.info("Connected to instrument at %s", self.address)

        except asyncio.TimeoutError:
            raise ConnectionError(
                f"Connection timed out after {self.timeout}s",
                self.address,
            )
        except OSError as e:
            raise ConnectionError(
                f"Failed to connect: {e}",
                self.address,
            )

    async def disconnect(self) -> None:
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except OSError as e:
                logger.warning("Error closing connection to %s: %s", self.address, e)
            finally:
                self._writer = None
                self._reader = None
                self._connected = False
                logger.info("Disconnected from %s", self.address)

    async def send(self, command: str) -> None:
        if not self.is_connected:
            raise ConnectionError("Not connected to instrument", self.address)

        async with self._lock:
            try:
                if not command.endswith(self.TERMINATOR):
                    command += self.TERMINATOR

                self._writer.write(command.encode())
                await self._writer.drain()
                logger.debug("Sent: %s", command.strip())

            except OSError as e:
                self._connected = False
                logger.error("Send failed to %s: %s", self.address, e)
                raise CommunicationError(f"Failed to send command: {e}", self.address)

    async def _read_response(self, timeout: float | None = None) -> str:
        """Read a line response from the instrument."""
        if not self.is_connected:
            raise ConnectionError("Not connected to instrument", self.address)

        timeout = timeout or self.command_timeout

        try:
            data = await asyncio.wait_for(
                self._reader.readline(),
                timeout=timeout,
            )
            response = data.decode().strip()
            logger.debug("Received: %s...", response[:100])
            return response

        except asyncio.TimeoutError:
            raise TimeoutError(f"Read timed out after {timeout}s", self.address)
        except OSError as e:
            self._connected = False
            logger.error("Read failed from %s: %s", self.address, e)
            raise CommunicationError(f"Failed to read response: {e}", self.address)

    async def query(self, command: str, timeout: float | None = None) -> str:
        if not self.is_connected:
            raise ConnectionError("Not connected to instrument", self.address)

        timeout = timeout or self.command_timeout

        async with self._lock:
            try:
                if not command.endswith(self.TERMINATOR):
                    command += self.TERMINATOR
                self._writer.write(command.encode())
                await self._writer.drain()
                logger.debug("Sent: %s", command.strip())
            except OSError as e:
                self._connected = False
                logger.error("Query send failed to %s: %s", self.address, e)
                raise CommunicationError(f"Failed to send command: {e}", self.address)

            try:
                data = await asyncio.wait_for(
                    self._reader.readline(),
                    timeout=timeout,
                )
                response = data.decode().strip()
                logger.debug("Received: %s...", response[:100])
                return response
            except asyncio.TimeoutError:
                raise TimeoutError(f"Read timed out after {timeout}s", self.address)
            except OSError as e:
                self._connected = False
                logger.error("Query read failed from %s: %s", self.address, e)
                raise CommunicationError(f"Failed to read response: {e}", self.address)

    async def query_binary(
        self,
        command: str,
        timeout: float | None = None,
    ) -> bytes:
        if not self.is_connected:
            raise ConnectionError("Not connected to instrument", self.address)

        timeout = timeout or self.command_timeout

        async with self._lock:
            try:
                if not command.endswith(self.TERMINATOR):
                    command += self.TERMINATOR
                self._writer.write(command.encode())
                await self._writer.drain()

                # Read header byte (#)
                header = await asyncio.wait_for(
                    self._reader.read(1),
                    timeout=timeout,
                )
                if header != b"#":
                    rest = await self._reader.readline()
                    return header + rest

                # Read length of length field
                len_len_byte = await self._reader.read(1)
                len_len = int(len_len_byte.decode())

                # Read data length
                data_len_bytes = await self._reader.read(len_len)
                data_len = int(data_len_bytes.decode())

                # Read binary data
                data = b""
                while len(data) < data_len:
                    chunk = await self._reader.read(min(data_len - len(data), self.BUFFER_SIZE))
                    if not chunk:
                        break
                    data += chunk

                # Read trailing newline
                await self._reader.read(1)

                logger.debug("Received %d bytes of binary data", len(data))
                return data

            except asyncio.TimeoutError:
                raise TimeoutError(f"Binary read timed out after {timeout}s", self.address)
            except (OSError, ValueError) as e:
                logger.error("Binary read failed from %s: %s", self.address, e)
                raise CommunicationError(f"Failed to read binary data: {e}", self.address)

    async def query_float_list(
        self,
        command: str,
        timeout: float | None = None,
    ) -> list[float]:
        response = await self.query(command, timeout)
        if not response:
            return []

        try:
            return [float(x) for x in response.split(",")]
        except ValueError as e:
            raise CommunicationError(f"Failed to parse float list: {e}", self.address)

    async def wait_opc(self, timeout: float | None = None) -> bool:
        response = await self.query("*OPC?", timeout)
        return response.strip() == "1"
