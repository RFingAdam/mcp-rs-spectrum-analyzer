"""Unified driver for spectrum/signal analyzers via SCPI."""

import logging
from enum import Enum

from ..exceptions import (
    ConfigurationError,
    MeasurementError,
    SpectrumAnalyzerError,
)
from ..models.sa_types import (
    ACLRResult,
    ChannelPowerResult,
    DetectorType,
    InstrumentInfo,
    MarkerData,
    OBWResult,
    SEMResult,
    SpectrumAnalyzerFamily,
    TraceData,
    TraceMode,
)
from ..safety.validators import SafetyLimits, SafetyValidator, sanitize_scpi_param
from ..transport import SCPITransport, TCPSocketTransport
from .scpi_socket import SCPISocket  # noqa: F401 – backward compat

logger = logging.getLogger(__name__)


def _parse_float(value: str, field_name: str = "value") -> float:
    """
    Parse a string to float with meaningful error messages.

    Args:
        value: String to parse
        field_name: Name of the field for error messages

    Returns:
        Parsed float value

    Raises:
        MeasurementError: If value cannot be parsed as float
    """
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        raise MeasurementError(f"Cannot parse {field_name}: '{value}' is not a valid number", "")


class ConnectionState(Enum):
    """Spectrum analyzer connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class RSSpectrumAnalyzerDriver:
    """
    Unified driver for spectrum/signal analyzers via SCPI.

    Supports multiple vendors (R&S, Keysight, Rigol, Siglent, Anritsu, Tektronix)
    through a common SCPI interface. Uses pluggable transports (TCP/IP, VISA).

    Example:
        async with RSSpectrumAnalyzerDriver("192.168.1.100", 5025) as sa:
            await sa.set_center_span(1e9, 100e6)
            await sa.single_sweep()
            trace = await sa.get_trace_data()
            print(f"Peak: {trace.peak_amplitude} dBm at {trace.peak_frequency/1e6} MHz")
    """

    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = 5025,
        timeout: float = 5.0,
        command_timeout: float = 30.0,
        safety_limits: SafetyLimits | None = None,
        family: SpectrumAnalyzerFamily | None = None,
        transport: SCPITransport | None = None,
    ):
        """
        Initialize spectrum analyzer driver.

        Args:
            host: Instrument hostname or IP address
            port: TCP port (default 5025)
            timeout: Connection timeout in seconds
            command_timeout: Command timeout in seconds
            safety_limits: Custom safety limits (uses defaults if None)
            family: Instrument family (auto-detected if None)
            transport: Pre-configured transport (overrides host/port/timeout)
        """
        self.host = host
        self.port = port

        if transport is not None:
            self._socket: SCPITransport = transport
        else:
            self._socket = TCPSocketTransport(host, port, timeout, command_timeout)
        self._validator = SafetyValidator(safety_limits)
        self._state = ConnectionState.DISCONNECTED
        self._info: InstrumentInfo | None = None
        self._family: SpectrumAnalyzerFamily | None = family
        self._last_error: str | None = None

    @property
    def is_connected(self) -> bool:
        """Check if connected to spectrum analyzer."""
        return self._state == ConnectionState.CONNECTED and self._socket.is_connected

    @property
    def state(self) -> ConnectionState:
        """Get connection state."""
        return self._state

    @property
    def info(self) -> InstrumentInfo | None:
        """Get instrument info (available after connect)."""
        return self._info

    @property
    def family(self) -> SpectrumAnalyzerFamily | None:
        """Get instrument family."""
        return self._family

    async def connect(self) -> InstrumentInfo:
        """
        Connect to spectrum analyzer and identify it.

        Returns:
            InstrumentInfo with identification details

        Raises:
            ConnectionError: If connection fails
        """
        self._state = ConnectionState.CONNECTING
        try:
            await self._socket.connect()

            # Identify instrument
            idn = await self._socket.query("*IDN?")
            self._info = InstrumentInfo.from_idn(idn)

            # Auto-detect family
            if self._family is None:
                self._family = self._info.detect_family()

            self._state = ConnectionState.CONNECTED
            logger.info(
                f"Connected to {self._info.manufacturer} {self._info.model} "
                f"(S/N: {self._info.serial_number})"
            )

            return self._info

        except (OSError, SpectrumAnalyzerError) as e:
            self._state = ConnectionState.ERROR
            self._last_error = str(e)
            logger.error("Connection failed to %s:%d: %s", self.host, self.port, e)
            raise

    async def disconnect(self) -> None:
        """Disconnect from spectrum analyzer."""
        await self._socket.disconnect()
        self._state = ConnectionState.DISCONNECTED
        logger.info("Disconnected from spectrum analyzer")

    async def __aenter__(self) -> "RSSpectrumAnalyzerDriver":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

    # =========================================================================
    # Raw SCPI
    # =========================================================================

    async def scpi_send(self, command: str) -> None:
        """Send raw SCPI command."""
        await self._socket.send(command)

    async def scpi_query(self, command: str, timeout: float | None = None) -> str:
        """Send raw SCPI query and return response."""
        return await self._socket.query(command, timeout)

    async def reset(self) -> None:
        """Reset instrument (*RST)."""
        await self._socket.send("*RST")
        await self._socket.wait_opc()
        logger.info("Instrument reset")

    async def preset(self) -> None:
        """Preset instrument (SYSTem:PRESet)."""
        await self._socket.send("SYST:PRES")
        await self._socket.wait_opc()
        logger.info("Instrument preset")

    async def get_error(self) -> str:
        """Query system error."""
        return await self._socket.query("SYST:ERR?")

    async def get_error_queue(self) -> list[str]:
        """Read all errors from the error queue until empty."""
        errors: list[str] = []
        for _ in range(100):  # safety limit
            resp = await self._socket.query("SYST:ERR?")
            if resp.startswith("0,") or resp.startswith('0,"'):
                break
            errors.append(resp)
        return errors

    async def set_sweep_points(self, points: int) -> None:
        """Set number of sweep points."""
        await self._socket.send(f"SENS:SWE:POIN {points}")

    async def get_sweep_points(self) -> int:
        """Get number of sweep points."""
        resp = await self._socket.query("SENS:SWE:POIN?")
        return int(_parse_float(resp, "sweep_points"))

    async def set_display_update(self, enabled: bool) -> None:
        """Enable/disable display updates for faster remote operation."""
        state = "ON" if enabled else "OFF"
        await self._socket.send(f"SYST:DISP:UPD {state}")

    async def capture_screenshot(self, fmt: str = "PNG") -> bytes:
        """Capture screenshot and return as bytes."""
        await self._socket.send(f"HCOP:DEV:LANG {fmt}")
        await self._socket.send("HCOP:DEST 'MMEM'")
        await self._socket.send("HCOP:IMM")
        await self._socket.wait_opc()
        return await self._socket.query_binary("HCOP:DATA?")

    async def run_alignment(self) -> str:
        """Run internal self-alignment/calibration."""
        resp = await self._socket.query("CAL:ALL?", timeout=120.0)
        return resp

    # =========================================================================
    # Frequency Control
    # =========================================================================

    async def set_center_frequency(self, freq_hz: float) -> None:
        """Set center frequency."""
        self._validator.validate_frequency(freq_hz)
        await self._socket.send(f"SENS:FREQ:CENT {freq_hz}")
        logger.debug(f"Center frequency set to {freq_hz / 1e6:.3f} MHz")

    async def set_span(self, span_hz: float) -> None:
        """Set frequency span. Use 0 for zero-span."""
        if span_hz < 0:
            raise ConfigurationError("Span cannot be negative")
        await self._socket.send(f"SENS:FREQ:SPAN {span_hz}")
        logger.debug(f"Span set to {span_hz / 1e6:.3f} MHz")

    async def set_center_span(self, center_hz: float, span_hz: float) -> None:
        """Set center frequency and span."""
        self._validator.validate_frequency(center_hz)
        await self.set_center_frequency(center_hz)
        await self.set_span(span_hz)

    async def set_start_stop(self, start_hz: float, stop_hz: float) -> None:
        """Set start and stop frequencies."""
        self._validator.validate_frequency_range(start_hz, stop_hz)
        await self._socket.send(f"SENS:FREQ:STAR {start_hz}")
        await self._socket.send(f"SENS:FREQ:STOP {stop_hz}")
        logger.debug(f"Frequency range set to {start_hz / 1e6:.3f} - {stop_hz / 1e6:.3f} MHz")

    async def set_frequency_step(self, step_hz: float) -> None:
        """Set frequency step for manual tuning."""
        await self._socket.send(f"SENS:FREQ:CENT:STEP {step_hz}")

    async def full_span(self) -> None:
        """Set full span."""
        await self._socket.send("SENS:FREQ:SPAN:FULL")
        logger.debug("Full span set")

    async def get_center_frequency(self) -> float:
        """Get current center frequency."""
        resp = await self._socket.query("SENS:FREQ:CENT?")
        return _parse_float(resp, "center_frequency")

    async def get_span(self) -> float:
        """Get current span."""
        resp = await self._socket.query("SENS:FREQ:SPAN?")
        return _parse_float(resp, "span")

    async def get_start_frequency(self) -> float:
        """Get current start frequency."""
        resp = await self._socket.query("SENS:FREQ:STAR?")
        return _parse_float(resp, "start_frequency")

    async def get_stop_frequency(self) -> float:
        """Get current stop frequency."""
        resp = await self._socket.query("SENS:FREQ:STOP?")
        return _parse_float(resp, "stop_frequency")

    # =========================================================================
    # Amplitude Control
    # =========================================================================

    async def set_reference_level(self, level_dbm: float) -> None:
        """Set reference level."""
        self._validator.validate_reference_level(level_dbm)
        await self._socket.send(f"DISP:TRAC:Y:RLEV {level_dbm}")
        logger.debug(f"Reference level set to {level_dbm} dBm")

    async def get_reference_level(self) -> float:
        """Get current reference level."""
        resp = await self._socket.query("DISP:TRAC:Y:RLEV?")
        return _parse_float(resp, "reference_level")

    async def set_attenuation(self, atten_db: float) -> None:
        """Set input attenuation."""
        self._validator.validate_attenuation(atten_db)
        await self._socket.send(f"INP:ATT {atten_db}")
        logger.debug(f"Attenuation set to {atten_db} dB")

    async def get_attenuation(self) -> float:
        """Get current input attenuation."""
        resp = await self._socket.query("INP:ATT?")
        return _parse_float(resp, "attenuation")

    async def set_preamp(self, enabled: bool) -> None:
        """Enable or disable preamplifier."""
        state = "ON" if enabled else "OFF"
        await self._socket.send(f"INP:GAIN:STAT {state}")
        logger.debug(f"Preamplifier {'enabled' if enabled else 'disabled'}")

    async def get_preamp(self) -> bool:
        """Get preamplifier state."""
        resp = await self._socket.query("INP:GAIN:STAT?")
        return resp.strip() in ("1", "ON")

    async def set_scale(self, db_per_div: float) -> None:
        """Set Y-axis scale in dB/division."""
        if db_per_div <= 0:
            raise ConfigurationError("Scale must be positive")
        await self._socket.send(f"DISP:TRAC:Y:PDIV {db_per_div}")
        logger.debug(f"Scale set to {db_per_div} dB/div")

    # =========================================================================
    # Bandwidth Control
    # =========================================================================

    async def set_rbw(self, rbw_hz: float) -> None:
        """Set resolution bandwidth."""
        self._validator.validate_rbw(rbw_hz)
        await self._socket.send("SENS:BAND:RES:AUTO OFF")
        await self._socket.send(f"SENS:BAND:RES {rbw_hz}")
        logger.debug(f"RBW set to {rbw_hz / 1e3:.1f} kHz")

    async def get_rbw(self) -> float:
        """Get current resolution bandwidth."""
        resp = await self._socket.query("SENS:BAND:RES?")
        return _parse_float(resp, "rbw")

    async def set_vbw(self, vbw_hz: float) -> None:
        """Set video bandwidth."""
        await self._socket.send("SENS:BAND:VID:AUTO OFF")
        await self._socket.send(f"SENS:BAND:VID {vbw_hz}")
        logger.debug(f"VBW set to {vbw_hz / 1e3:.1f} kHz")

    async def get_vbw(self) -> float:
        """Get current video bandwidth."""
        resp = await self._socket.query("SENS:BAND:VID?")
        return _parse_float(resp, "vbw")

    async def set_sweep_time(self, time_s: float) -> None:
        """Set sweep time."""
        if time_s <= 0:
            raise ConfigurationError("Sweep time must be positive")
        await self._socket.send("SENS:SWE:TIME:AUTO OFF")
        await self._socket.send(f"SENS:SWE:TIME {time_s}")
        logger.debug(f"Sweep time set to {time_s} s")

    async def get_sweep_time(self) -> float:
        """Get current sweep time."""
        resp = await self._socket.query("SENS:SWE:TIME?")
        return _parse_float(resp, "sweep_time")

    async def auto_coupling(self) -> None:
        """Enable auto-coupling for RBW, VBW, and sweep time."""
        await self._socket.send("SENS:BAND:RES:AUTO ON")
        await self._socket.send("SENS:BAND:VID:AUTO ON")
        await self._socket.send("SENS:SWE:TIME:AUTO ON")
        logger.debug("Auto-coupling enabled for RBW, VBW, sweep time")

    # =========================================================================
    # Trace Operations
    # =========================================================================

    async def get_trace_data(self, trace_number: int = 1) -> TraceData:
        """
        Read trace data from instrument.

        Args:
            trace_number: Trace number (1-6)

        Returns:
            TraceData with frequencies and amplitudes
        """
        # Get frequency parameters to build frequency axis
        start = await self.get_start_frequency()
        stop = await self.get_stop_frequency()

        # Get trace data (comma-separated amplitude values)
        amplitudes = await self._socket.query_float_list(f"TRAC:DATA? TRACE{trace_number}")

        # Build frequency array
        num_points = len(amplitudes)
        if num_points > 1:
            step = (stop - start) / (num_points - 1)
            frequencies = [start + i * step for i in range(num_points)]
        elif num_points == 1:
            frequencies = [start]
        else:
            frequencies = []

        # Get additional metadata
        rbw = await self.get_rbw()
        vbw = await self.get_vbw()
        ref_level = await self.get_reference_level()

        return TraceData(
            frequencies=frequencies,
            amplitudes=amplitudes,
            trace_number=trace_number,
            rbw_hz=rbw,
            vbw_hz=vbw,
            reference_level_dbm=ref_level,
        )

    async def set_trace_mode(self, mode: TraceMode, trace_number: int = 1) -> None:
        """Set trace mode."""
        await self._socket.send(f"DISP:TRAC{trace_number}:MODE {mode.value}")
        logger.debug(f"Trace {trace_number} mode set to {mode.value}")

    async def set_detector(self, detector: DetectorType, trace_number: int = 1) -> None:
        """Set detector type."""
        await self._socket.send(f"SENS:DET{trace_number} {detector.value}")
        logger.debug(f"Detector {trace_number} set to {detector.value}")

    async def set_averaging_count(self, count: int) -> None:
        """Set trace averaging count."""
        if count < 0:
            raise ConfigurationError("Average count must be non-negative")
        if count <= 1:
            await self._socket.send("SENS:AVER:STAT OFF")
        else:
            await self._socket.send("SENS:AVER:STAT ON")
            await self._socket.send(f"SENS:AVER:COUN {count}")
        logger.debug(f"Averaging count set to {count}")

    async def clear_trace(self, trace_number: int = 1) -> None:
        """Clear/reset trace data."""
        await self._socket.send(f"DISP:TRAC{trace_number}:MODE WRITe")
        logger.debug(f"Trace {trace_number} cleared")

    # =========================================================================
    # Marker Operations
    # =========================================================================

    async def set_marker(self, frequency_hz: float, marker_number: int = 1) -> None:
        """Position a marker at a specific frequency."""
        self._validator.validate_frequency(frequency_hz)
        await self._socket.send(f"CALC:MARK{marker_number}:STAT ON")
        await self._socket.send(f"CALC:MARK{marker_number}:X {frequency_hz}")
        logger.debug(f"Marker {marker_number} set to {frequency_hz / 1e6:.3f} MHz")

    async def get_marker(self, marker_number: int = 1) -> MarkerData:
        """Read marker position and value."""
        freq_resp = await self._socket.query(f"CALC:MARK{marker_number}:X?")
        amp_resp = await self._socket.query(f"CALC:MARK{marker_number}:Y?")

        return MarkerData(
            marker_number=marker_number,
            frequency_hz=_parse_float(freq_resp, "marker_frequency"),
            amplitude_dbm=_parse_float(amp_resp, "marker_amplitude"),
        )

    async def peak_search(self, marker_number: int = 1) -> MarkerData:
        """Find peak on trace and position marker."""
        await self._socket.send(f"CALC:MARK{marker_number}:STAT ON")
        await self._socket.send(f"CALC:MARK{marker_number}:MAX")
        return await self.get_marker(marker_number)

    async def next_peak(self, marker_number: int = 1, direction: str = "next") -> MarkerData:
        """
        Find next peak from current marker position.

        Args:
            marker_number: Marker number
            direction: "next", "left", or "right"
        """
        cmd_map = {
            "next": f"CALC:MARK{marker_number}:MAX:NEXT",
            "left": f"CALC:MARK{marker_number}:MAX:LEFT",
            "right": f"CALC:MARK{marker_number}:MAX:RIGH",
        }
        cmd = cmd_map.get(direction, cmd_map["next"])
        await self._socket.send(cmd)
        return await self.get_marker(marker_number)

    async def marker_to_center(self, marker_number: int = 1) -> None:
        """Set center frequency to marker frequency."""
        marker = await self.get_marker(marker_number)
        await self.set_center_frequency(marker.frequency_hz)
        logger.debug(f"Center frequency set to marker {marker_number}")

    async def set_delta_marker(self, marker_number: int = 1, enabled: bool = True) -> None:
        """Enable/disable delta marker."""
        state = "ON" if enabled else "OFF"
        await self._socket.send(f"CALC:DELT{marker_number}:STAT {state}")
        logger.debug(f"Delta marker {marker_number} {'enabled' if enabled else 'disabled'}")

    async def marker_bandwidth(self, n_db: float = 3.0, marker_number: int = 1) -> dict:
        """
        Measure N-dB bandwidth using marker.

        Args:
            n_db: Bandwidth criteria in dB (default 3 dB)
            marker_number: Marker number

        Returns:
            Dictionary with bandwidth results
        """
        await self._socket.send(f"CALC:MARK{marker_number}:FUNC:BWID:STAT ON")
        await self._socket.send(f"CALC:MARK{marker_number}:FUNC:BWID:NDB {n_db}")
        bw_resp = await self._socket.query(f"CALC:MARK{marker_number}:FUNC:BWID:RES?")

        # Response is typically: bandwidth,center_freq,quality_factor
        parts = bw_resp.split(",")
        result = {"n_db": n_db, "bandwidth_hz": _parse_float(parts[0], "bandwidth")}
        if len(parts) > 1:
            result["center_frequency_hz"] = _parse_float(parts[1], "center_freq")
        if len(parts) > 2:
            result["quality_factor"] = _parse_float(parts[2], "q_factor")
        return result

    # =========================================================================
    # Sweep Control
    # =========================================================================

    async def single_sweep(self, timeout: float | None = None) -> None:
        """Trigger single sweep and wait for completion."""
        await self._socket.send("INIT:CONT OFF")
        await self._socket.send("INIT:IMM")
        await self._socket.wait_opc(timeout)
        logger.debug("Single sweep complete")

    async def continuous_sweep(self, enabled: bool = True) -> None:
        """Enable or disable continuous sweep."""
        state = "ON" if enabled else "OFF"
        await self._socket.send(f"INIT:CONT {state}")
        logger.debug(f"Continuous sweep {'enabled' if enabled else 'disabled'}")

    async def set_trigger(self, source: str = "IMM", level: float | None = None) -> None:
        """
        Configure trigger source.

        Args:
            source: Trigger source (IMM, EXT, VID, IFP, RFP)
            level: Trigger level (for video/IF power triggers)
        """
        source = sanitize_scpi_param(source)
        await self._socket.send(f"TRIG:SOUR {source}")
        if level is not None and source in ("VID", "IFP"):
            await self._socket.send(f"TRIG:LEV {level}")
        logger.debug(f"Trigger set to {source}")

    # =========================================================================
    # Measurements
    # =========================================================================

    async def measure_channel_power(
        self,
        center_hz: float,
        bandwidth_hz: float,
    ) -> ChannelPowerResult:
        """
        Measure channel power.

        Args:
            center_hz: Center frequency in Hz
            bandwidth_hz: Channel bandwidth in Hz

        Returns:
            ChannelPowerResult with power measurements
        """
        self._validator.validate_frequency(center_hz)

        # Configure channel power measurement
        await self._socket.send("CALC:MARK:FUNC:POW:SEL CPOW")
        await self._socket.send(f"SENS:FREQ:CENT {center_hz}")
        await self._socket.send(f"SENS:POW:ACH:BWID:CHAN1 {bandwidth_hz}")

        # Set appropriate span (at least 2x bandwidth)
        await self._socket.send(f"SENS:FREQ:SPAN {bandwidth_hz * 3}")

        # Trigger measurement
        await self.single_sweep()

        # Read result
        resp = await self._socket.query("CALC:MARK:FUNC:POW:RES? CPOW")
        parts = resp.split(",")

        ch_power = _parse_float(parts[0], "channel_power")
        ch_density = (
            _parse_float(parts[1], "power_density") if len(parts) > 1 else ch_power - 10 * 1.0
        )  # noqa: E501

        return ChannelPowerResult(
            channel_power_dbm=ch_power,
            channel_power_density_dbm_hz=ch_density,
            channel_bandwidth_hz=bandwidth_hz,
            center_frequency_hz=center_hz,
        )

    async def measure_aclr(
        self,
        center_hz: float,
        channel_bw_hz: float,
        adjacent_bw_hz: float | None = None,
        adjacent_offset_hz: float | None = None,
    ) -> ACLRResult:
        """
        Measure adjacent channel leakage ratio.

        Args:
            center_hz: Center frequency in Hz
            channel_bw_hz: Channel bandwidth in Hz
            adjacent_bw_hz: Adjacent channel bandwidth (defaults to channel_bw)
            adjacent_offset_hz: Adjacent channel offset (defaults to channel_bw)

        Returns:
            ACLRResult with ACLR measurements
        """
        self._validator.validate_frequency(center_hz)

        adj_bw = adjacent_bw_hz or channel_bw_hz
        adj_offset = adjacent_offset_hz or channel_bw_hz

        # Configure ACLR measurement
        await self._socket.send("CALC:MARK:FUNC:POW:SEL ACP")
        await self._socket.send(f"SENS:FREQ:CENT {center_hz}")
        await self._socket.send(f"SENS:POW:ACH:BWID:CHAN1 {channel_bw_hz}")
        await self._socket.send(f"SENS:POW:ACH:BWID:ACH {adj_bw}")
        await self._socket.send(f"SENS:POW:ACH:SPAC {adj_offset}")

        # Set span to cover all channels
        total_span = adj_offset * 2 + channel_bw_hz * 2
        await self._socket.send(f"SENS:FREQ:SPAN {total_span}")

        # Trigger measurement
        await self.single_sweep()

        # Read result
        resp = await self._socket.query("CALC:MARK:FUNC:POW:RES? ACP")
        parts = resp.split(",")

        # Parse: channel_power, lower_adj, upper_adj, lower_aclr, upper_aclr
        ch_power = _parse_float(parts[0], "channel_power")
        lower_adj = _parse_float(parts[1], "lower_adjacent") if len(parts) > 1 else 0.0
        upper_adj = _parse_float(parts[2], "upper_adjacent") if len(parts) > 2 else 0.0

        return ACLRResult(
            channel_power_dbm=ch_power,
            lower_adjacent_dbm=lower_adj,
            upper_adjacent_dbm=upper_adj,
            lower_aclr_db=ch_power - lower_adj,
            upper_aclr_db=ch_power - upper_adj,
        )

    async def measure_obw(
        self,
        power_percentage: float = 99.0,
    ) -> OBWResult:
        """
        Measure occupied bandwidth.

        Args:
            power_percentage: Power percentage (default 99%)

        Returns:
            OBWResult with occupied bandwidth
        """
        # Configure OBW measurement
        await self._socket.send("CALC:MARK:FUNC:POW:SEL OBW")
        await self._socket.send(f"SENS:POW:ACH:BWID:PCT {power_percentage}")

        # Trigger measurement
        await self.single_sweep()

        # Read result
        resp = await self._socket.query("CALC:MARK:FUNC:POW:RES? OBW")
        parts = resp.split(",")

        obw = _parse_float(parts[0], "occupied_bandwidth")
        center = await self.get_center_frequency()

        return OBWResult(
            occupied_bandwidth_hz=obw,
            center_frequency_hz=center,
            power_percentage=power_percentage,
        )

    async def measure_sem(self) -> SEMResult:
        """
        Measure spectrum emission mask.

        Returns:
            SEMResult with pass/fail and violations
        """
        # Activate SEM measurement
        await self._socket.send("CALC:MARK:FUNC:POW:SEL ESP")

        # Trigger measurement
        await self.single_sweep()

        # Read result
        resp = await self._socket.query("CALC:MARK:FUNC:POW:RES? ESP")
        parts = resp.split(",")

        # Parse TX power (first value)
        tx_power = _parse_float(parts[0], "tx_power") if parts else 0.0

        # Check for violations
        # SEM results vary by configuration; simplified parsing
        passed = True
        violations = []
        for i in range(1, len(parts), 3):
            if i + 2 < len(parts):
                try:
                    limit = float(parts[i])
                    measured = float(parts[i + 1])
                    if measured > limit:
                        passed = False
                        violations.append(
                            {
                                "limit_dbm": limit,
                                "measured_dbm": measured,
                                "margin_db": limit - measured,
                            }
                        )
                except (ValueError, IndexError) as e:
                    logger.debug("Skipping unparseable SEM segment at index %d: %s", i, e)

        return SEMResult(
            passed=passed,
            tx_power_dbm=tx_power,
            violations=violations,
        )

    async def get_status(self) -> dict:
        """Get comprehensive instrument status."""
        status = {
            "connected": self.is_connected,
            "state": self._state.value,
            "address": f"{self.host}:{self.port}",
        }

        if self._info:
            status["instrument"] = self._info.to_dict()

        if self._family:
            status["family"] = self._family.value

        if self.is_connected:
            try:
                status["center_frequency_hz"] = await self.get_center_frequency()
                status["span_hz"] = await self.get_span()
                status["reference_level_dbm"] = await self.get_reference_level()
                status["rbw_hz"] = await self.get_rbw()
                status["vbw_hz"] = await self.get_vbw()
                status["attenuation_db"] = await self.get_attenuation()
            except (SpectrumAnalyzerError, ValueError) as e:
                logger.warning("Failed to query instrument status details: %s", e)
                status["query_error"] = str(e)

        if self._last_error:
            status["last_error"] = self._last_error

        return status
