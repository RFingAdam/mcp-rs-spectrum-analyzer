"""VISA transport for SCPI instruments (optional dependency).

Supports TCPIP, GPIB, USB-TMC, HiSLIP, and VXI-11 resource strings
via pyvisa. Install with: ``pip install spectrum-analyzer-mcp[visa]``
"""

import asyncio
import logging
from functools import partial

from ..exceptions import CommunicationError, ConnectionError, TimeoutError
from .base import SCPITransport

logger = logging.getLogger(__name__)

try:
    import pyvisa

    PYVISA_AVAILABLE = True
except ImportError:
    pyvisa = None  # type: ignore[assignment]
    PYVISA_AVAILABLE = False


class VISATransport(SCPITransport):
    """VISA-based SCPI transport.

    Wraps pyvisa (synchronous) in ``asyncio.run_in_executor()`` for async
    compatibility. Supports resource strings like:

    - ``TCPIP::<ip>::<port>::SOCKET`` (raw socket via VISA)
    - ``TCPIP::<ip>::INSTR`` (VXI-11)
    - ``TCPIP::<ip>::hislip0::INSTR`` (HiSLIP)
    - ``GPIB::<addr>::INSTR``
    - ``USB::<vid>::<pid>::<serial>::INSTR`` (USB-TMC)

    Requires: ``pip install pyvisa pyvisa-py``
    """

    def __init__(
        self,
        resource_string: str,
        timeout: float = 5.0,
        command_timeout: float = 30.0,
    ):
        if not PYVISA_AVAILABLE:
            raise ImportError(
                "pyvisa is required for VISA transport. "
                "Install with: pip install spectrum-analyzer-mcp[visa]"
            )

        self._resource_string = resource_string
        self._timeout_ms = int(timeout * 1000)
        self._command_timeout_ms = int(command_timeout * 1000)
        self._rm: pyvisa.ResourceManager | None = None
        self._inst: pyvisa.resources.Resource | None = None
        self._lock = asyncio.Lock()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._inst is not None

    @property
    def address(self) -> str:
        return self._resource_string

    async def connect(self) -> None:
        if self._connected:
            return

        loop = asyncio.get_running_loop()
        try:
            self._rm = await loop.run_in_executor(None, pyvisa.ResourceManager)
            open_fn = partial(
                self._rm.open_resource,
                self._resource_string,
                timeout=self._timeout_ms,
            )
            self._inst = await loop.run_in_executor(None, open_fn)
            self._inst.timeout = self._command_timeout_ms

            # Configure for SOCKET resources
            if "SOCKET" in self._resource_string.upper():
                self._inst.read_termination = "\n"
                self._inst.write_termination = "\n"

            self._connected = True
            logger.info("VISA connected to %s", self.address)

        except Exception as e:
            self._connected = False
            raise ConnectionError(f"VISA connection failed: {e}", self.address)

    async def disconnect(self) -> None:
        loop = asyncio.get_running_loop()
        if self._inst is not None:
            try:
                await loop.run_in_executor(None, self._inst.close)
            except Exception as e:
                logger.warning("Error closing VISA resource %s: %s", self.address, e)
            finally:
                self._inst = None
                self._connected = False

        if self._rm is not None:
            try:
                await loop.run_in_executor(None, self._rm.close)
            except Exception:
                pass
            finally:
                self._rm = None

        logger.info("VISA disconnected from %s", self.address)

    async def send(self, command: str) -> None:
        if not self.is_connected:
            raise ConnectionError("Not connected via VISA", self.address)

        loop = asyncio.get_running_loop()
        async with self._lock:
            try:
                await loop.run_in_executor(None, self._inst.write, command)
                logger.debug("VISA sent: %s", command.strip())
            except Exception as e:
                self._connected = False
                raise CommunicationError(f"VISA write failed: {e}", self.address)

    async def query(self, command: str, timeout: float | None = None) -> str:
        if not self.is_connected:
            raise ConnectionError("Not connected via VISA", self.address)

        loop = asyncio.get_running_loop()
        async with self._lock:
            old_timeout = self._inst.timeout
            if timeout is not None:
                self._inst.timeout = int(timeout * 1000)
            try:
                response = await loop.run_in_executor(None, self._inst.query, command)
                logger.debug("VISA query: %s -> %s...", command, response[:100])
                return response.strip()
            except pyvisa.errors.VisaIOError as e:
                if "timeout" in str(e).lower():
                    raise TimeoutError(f"VISA query timed out: {e}", self.address)
                self._connected = False
                raise CommunicationError(f"VISA query failed: {e}", self.address)
            except Exception as e:
                self._connected = False
                raise CommunicationError(f"VISA query failed: {e}", self.address)
            finally:
                if self._inst is not None:
                    self._inst.timeout = old_timeout

    async def query_binary(self, command: str, timeout: float | None = None) -> bytes:
        if not self.is_connected:
            raise ConnectionError("Not connected via VISA", self.address)

        loop = asyncio.get_running_loop()
        async with self._lock:
            old_timeout = self._inst.timeout
            if timeout is not None:
                self._inst.timeout = int(timeout * 1000)
            try:
                read_fn = partial(
                    self._inst.query_binary_values,
                    command,
                    datatype="B",
                    container=bytes,
                )
                data = await loop.run_in_executor(None, read_fn)
                logger.debug("VISA binary query: %d bytes", len(data))
                return data
            except pyvisa.errors.VisaIOError as e:
                if "timeout" in str(e).lower():
                    raise TimeoutError(f"VISA binary read timed out: {e}", self.address)
                raise CommunicationError(f"VISA binary read failed: {e}", self.address)
            except Exception as e:
                raise CommunicationError(f"VISA binary read failed: {e}", self.address)
            finally:
                if self._inst is not None:
                    self._inst.timeout = old_timeout

    async def query_float_list(self, command: str, timeout: float | None = None) -> list[float]:
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

    @staticmethod
    async def list_resources() -> list[str]:
        """List available VISA resources.

        Returns empty list if pyvisa is not installed.
        """
        if not PYVISA_AVAILABLE:
            return []

        loop = asyncio.get_running_loop()
        try:
            rm = await loop.run_in_executor(None, pyvisa.ResourceManager)
            resources = await loop.run_in_executor(None, rm.list_resources)
            await loop.run_in_executor(None, rm.close)
            return list(resources)
        except Exception as e:
            logger.warning("Failed to list VISA resources: %s", e)
            return []
