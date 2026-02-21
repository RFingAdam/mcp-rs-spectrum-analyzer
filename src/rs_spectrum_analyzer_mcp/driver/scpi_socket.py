"""Async TCP/IP SCPI transport for Rohde & Schwarz spectrum analyzers."""

import asyncio
import logging

from .exceptions import CommunicationError, ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class SCPISocket:
    """
    Async TCP/IP socket transport for SCPI commands.

    This class handles low-level communication with R&S spectrum
    analyzers via TCP/IP socket on port 5025.

    Example:
        async with SCPISocket("192.168.1.100", 5025) as scpi:
            idn = await scpi.query("*IDN?")
            print(f"Connected to: {idn}")

            await scpi.send("SENS:FREQ:CENT 1e9")
            await scpi.send("SENS:FREQ:SPAN 100e6")
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
        """
        Initialize SCPI socket connection.

        Args:
            host: Instrument hostname or IP address
            port: TCP port (default 5025)
            timeout: Connection timeout in seconds
            command_timeout: Default timeout for commands in seconds
        """
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
        """Check if socket is connected."""
        return self._connected and self._writer is not None

    @property
    def address(self) -> str:
        """Return address string for error messages."""
        return f"{self.host}:{self.port}"

    async def connect(self) -> None:
        """
        Establish TCP connection to instrument.

        Raises:
            ConnectionError: If connection fails
        """
        if self._connected:
            return

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            self._connected = True
            logger.info(f"Connected to spectrum analyzer at {self.address}")

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
        """Close TCP connection."""
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
                logger.info(f"Disconnected from {self.address}")

    async def send(self, command: str) -> None:
        """
        Send SCPI command without waiting for response.

        Args:
            command: SCPI command string

        Raises:
            ConnectionError: If not connected
            CommunicationError: If send fails
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to spectrum analyzer", self.address)

        async with self._lock:
            try:
                # Add terminator if not present
                if not command.endswith(self.TERMINATOR):
                    command += self.TERMINATOR

                self._writer.write(command.encode())
                await self._writer.drain()
                logger.debug(f"Sent: {command.strip()}")

            except OSError as e:
                self._connected = False
                logger.error("Send failed to %s: %s", self.address, e)
                raise CommunicationError(f"Failed to send command: {e}", self.address)

    async def read_response(self, timeout: float | None = None) -> str:
        """
        Read response from instrument.

        Args:
            timeout: Read timeout in seconds (uses command_timeout if None)

        Returns:
            Response string (without terminator)

        Raises:
            TimeoutError: If read times out
            CommunicationError: If read fails
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to spectrum analyzer", self.address)

        timeout = timeout or self.command_timeout

        try:
            data = await asyncio.wait_for(
                self._reader.readline(),
                timeout=timeout,
            )
            response = data.decode().strip()
            logger.debug(f"Received: {response[:100]}...")
            return response

        except asyncio.TimeoutError:
            raise TimeoutError(f"Read timed out after {timeout}s", self.address)
        except OSError as e:
            self._connected = False
            logger.error("Read failed from %s: %s", self.address, e)
            raise CommunicationError(f"Failed to read response: {e}", self.address)

    async def query(self, command: str, timeout: float | None = None) -> str:
        """
        Send query and wait for response.

        Args:
            command: SCPI query (should end with '?')
            timeout: Response timeout in seconds

        Returns:
            Response string

        Raises:
            ConnectionError: If not connected
            TimeoutError: If response times out
            CommunicationError: If communication fails
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to spectrum analyzer", self.address)

        timeout = timeout or self.command_timeout

        async with self._lock:
            try:
                if not command.endswith(self.TERMINATOR):
                    command += self.TERMINATOR
                self._writer.write(command.encode())
                await self._writer.drain()
                logger.debug(f"Sent: {command.strip()}")
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
                logger.debug(f"Received: {response[:100]}...")
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
        """
        Send query and read binary response.

        Used for retrieving trace data in binary format.

        Args:
            command: SCPI query
            timeout: Response timeout

        Returns:
            Binary data bytes
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to spectrum analyzer", self.address)

        timeout = timeout or self.command_timeout

        async with self._lock:
            try:
                # Send command
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
                    # Not binary format, read as text
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

                logger.debug(f"Received {len(data)} bytes of binary data")
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
        """
        Query and parse comma-separated float values.

        Args:
            command: SCPI query
            timeout: Response timeout

        Returns:
            List of float values
        """
        response = await self.query(command, timeout)
        if not response:
            return []

        try:
            return [float(x) for x in response.split(",")]
        except ValueError as e:
            raise CommunicationError(f"Failed to parse float list: {e}", self.address)

    async def wait_opc(self, timeout: float | None = None) -> bool:
        """
        Wait for operation complete (*OPC?).

        Args:
            timeout: Timeout in seconds

        Returns:
            True when operation completes
        """
        response = await self.query("*OPC?", timeout)
        return response.strip() == "1"

    async def __aenter__(self) -> "SCPISocket":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
