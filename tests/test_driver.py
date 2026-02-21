"""Tests for the spectrum analyzer driver."""

from unittest.mock import AsyncMock

import pytest

from rs_spectrum_analyzer_mcp.driver.sa_driver import (
    ConnectionState,
    RSSpectrumAnalyzerDriver,
    _parse_float,
)
from rs_spectrum_analyzer_mcp.exceptions import (
    ConfigurationError,
    MeasurementError,
    SafetyError,
)
from rs_spectrum_analyzer_mcp.models.sa_types import (
    DetectorType,
    InstrumentInfo,
    SpectrumAnalyzerFamily,
    TraceMode,
)


class TestParseFloat:
    """Test _parse_float utility."""

    def test_valid_float(self):
        assert _parse_float("1.5e9", "freq") == 1.5e9

    def test_valid_negative(self):
        assert _parse_float("-60.5", "amp") == -60.5

    def test_with_whitespace(self):
        assert _parse_float("  100.0  ", "val") == 100.0

    def test_invalid_raises(self):
        with pytest.raises(MeasurementError):
            _parse_float("abc", "test_field")


class TestConnectionState:
    """Test ConnectionState enum."""

    def test_states(self):
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTED.value == "connected"


class TestRSSpectrumAnalyzerDriver:
    """Test RSSpectrumAnalyzerDriver."""

    def _make_driver(self, mock_socket=None):
        driver = RSSpectrumAnalyzerDriver(
            host="192.168.1.100",
            port=5025,
        )
        if mock_socket:
            driver._socket = mock_socket
        return driver

    def test_initial_state(self):
        driver = self._make_driver()
        assert driver.is_connected is False
        assert driver.state == ConnectionState.DISCONNECTED
        assert driver.info is None
        assert driver.family is None

    @pytest.mark.asyncio
    async def test_connect(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.connect = AsyncMock()
        mock_socket.query = AsyncMock(
            return_value="Rohde&Schwarz,FSW-26,1312.8000K26/100001,4.30.018.28"
        )

        driver = self._make_driver(mock_socket)
        info = await driver.connect()

        assert driver.is_connected is True
        assert driver.state == ConnectionState.CONNECTED
        assert info.model == "FSW-26"
        assert driver.family == SpectrumAnalyzerFamily.FSW

    @pytest.mark.asyncio
    async def test_disconnect(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.connect = AsyncMock()
        mock_socket.disconnect = AsyncMock()
        mock_socket.query = AsyncMock(
            return_value="Rohde&Schwarz,FSW-26,SN123,1.0"
        )

        driver = self._make_driver(mock_socket)
        await driver.connect()
        await driver.disconnect()
        assert driver.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_set_center_frequency(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.send = AsyncMock()

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        await driver.set_center_frequency(1e9)
        mock_socket.send.assert_called_with("SENS:FREQ:CENT 1000000000.0")

    @pytest.mark.asyncio
    async def test_set_center_frequency_too_high(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        with pytest.raises(SafetyError):
            await driver.set_center_frequency(100e9)  # > 90 GHz

    @pytest.mark.asyncio
    async def test_set_span(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.send = AsyncMock()

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        await driver.set_span(100e6)
        mock_socket.send.assert_called_with("SENS:FREQ:SPAN 100000000.0")

    @pytest.mark.asyncio
    async def test_set_span_negative_raises(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        with pytest.raises(ConfigurationError):
            await driver.set_span(-100e6)

    @pytest.mark.asyncio
    async def test_set_reference_level(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.send = AsyncMock()

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        await driver.set_reference_level(-20.0)
        mock_socket.send.assert_called_with("DISP:TRAC:Y:RLEV -20.0")

    @pytest.mark.asyncio
    async def test_set_attenuation(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.send = AsyncMock()

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        await driver.set_attenuation(20.0)
        mock_socket.send.assert_called_with("INP:ATT 20.0")

    @pytest.mark.asyncio
    async def test_set_attenuation_too_high(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        with pytest.raises(SafetyError):
            await driver.set_attenuation(80.0)  # > 75 dB

    @pytest.mark.asyncio
    async def test_set_rbw(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.send = AsyncMock()

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        await driver.set_rbw(10e3)
        # Should first disable auto RBW, then set RBW
        assert mock_socket.send.call_count == 2

    @pytest.mark.asyncio
    async def test_set_preamp(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.send = AsyncMock()

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        await driver.set_preamp(True)
        mock_socket.send.assert_called_with("INP:GAIN:STAT ON")

    @pytest.mark.asyncio
    async def test_single_sweep(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.send = AsyncMock()
        mock_socket.wait_opc = AsyncMock(return_value=True)

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        await driver.single_sweep()
        assert mock_socket.send.call_count == 2  # INIT:CONT OFF + INIT:IMM

    @pytest.mark.asyncio
    async def test_get_trace_data(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.query = AsyncMock(side_effect=[
            "1000000000.0",  # start freq
            "2000000000.0",  # stop freq
            "1000000.0",     # rbw
            "3000000.0",     # vbw
            "0.0",           # ref level
        ])
        mock_socket.query_float_list = AsyncMock(
            return_value=[-80.0, -70.0, -60.0, -70.0, -80.0]
        )

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        trace = await driver.get_trace_data()

        assert trace.num_points == 5
        assert trace.peak_amplitude == -60.0
        assert len(trace.frequencies) == 5

    @pytest.mark.asyncio
    async def test_set_trace_mode(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.send = AsyncMock()

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        await driver.set_trace_mode(TraceMode.MAX_HOLD)
        mock_socket.send.assert_called_with("DISP:TRAC1:MODE MAXHold")

    @pytest.mark.asyncio
    async def test_set_detector(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.send = AsyncMock()

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        await driver.set_detector(DetectorType.QUASI_PEAK)
        mock_socket.send.assert_called_with("SENS:DET1 QPE")

    @pytest.mark.asyncio
    async def test_peak_search(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.send = AsyncMock()
        mock_socket.query = AsyncMock(side_effect=[
            "1500000000.0",  # marker freq
            "-45.5",          # marker amplitude
        ])

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        marker = await driver.peak_search()
        assert marker.frequency_hz == 1.5e9
        assert marker.amplitude_dbm == -45.5

    @pytest.mark.asyncio
    async def test_reset(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.send = AsyncMock()
        mock_socket.wait_opc = AsyncMock(return_value=True)

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        await driver.reset()
        mock_socket.send.assert_called_with("*RST")

    @pytest.mark.asyncio
    async def test_auto_coupling(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.send = AsyncMock()

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        await driver.auto_coupling()
        assert mock_socket.send.call_count == 3  # RBW, VBW, sweep time auto

    @pytest.mark.asyncio
    async def test_set_sweep_time_negative_raises(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        with pytest.raises(ConfigurationError):
            await driver.set_sweep_time(-1.0)

    @pytest.mark.asyncio
    async def test_get_status_connected(self):
        mock_socket = AsyncMock()
        mock_socket.is_connected = True
        mock_socket.query = AsyncMock(side_effect=[
            "1000000000.0",  # center
            "100000000.0",   # span
            "0.0",           # ref level
            "1000.0",        # rbw
            "3000.0",        # vbw
            "10.0",          # attenuation
        ])

        driver = self._make_driver(mock_socket)
        driver._state = ConnectionState.CONNECTED
        driver._info = InstrumentInfo("R&S", "FSW-26", "SN123", "1.0")
        driver._family = SpectrumAnalyzerFamily.FSW

        status = await driver.get_status()
        assert status["connected"] is True
        assert status["family"] == "FSW"
        assert status["center_frequency_hz"] == 1e9
