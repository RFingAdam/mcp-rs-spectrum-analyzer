"""Tests for state management."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from spectrum_analyzer_mcp.exceptions import CommunicationError, SpectrumAnalyzerError
from spectrum_analyzer_mcp.state import (
    AmplitudeState,
    BandwidthState,
    FrequencyState,
    InstrumentState,
    MarkerState,
    StateManager,
)


class TestFrequencyState:
    """Test FrequencyState."""

    def test_to_dict_roundtrip(self):
        state = FrequencyState(
            center_frequency_hz=1e9,
            span_hz=100e6,
            start_frequency_hz=950e6,
            stop_frequency_hz=1050e6,
        )
        d = state.to_dict()
        restored = FrequencyState.from_dict(d)
        assert restored.center_frequency_hz == 1e9
        assert restored.span_hz == 100e6


class TestAmplitudeState:
    """Test AmplitudeState."""

    def test_to_dict_roundtrip(self):
        state = AmplitudeState(
            reference_level_dbm=0.0,
            attenuation_db=10.0,
            preamp_enabled=True,
            scale_db_per_div=10.0,
        )
        d = state.to_dict()
        restored = AmplitudeState.from_dict(d)
        assert restored.reference_level_dbm == 0.0
        assert restored.preamp_enabled is True


class TestBandwidthState:
    """Test BandwidthState."""

    def test_to_dict_roundtrip(self):
        state = BandwidthState(
            rbw_hz=1e3,
            vbw_hz=3e3,
            sweep_time_s=0.5,
        )
        d = state.to_dict()
        restored = BandwidthState.from_dict(d)
        assert restored.rbw_hz == 1e3
        assert restored.vbw_hz == 3e3


class TestMarkerState:
    """Test MarkerState."""

    def test_enabled_marker(self):
        state = MarkerState(
            marker_number=1,
            enabled=True,
            frequency_hz=1e9,
            amplitude_dbm=-50.0,
        )
        d = state.to_dict()
        restored = MarkerState.from_dict(d)
        assert restored.enabled is True
        assert restored.frequency_hz == 1e9

    def test_disabled_marker(self):
        state = MarkerState(marker_number=2, enabled=False)
        d = state.to_dict()
        restored = MarkerState.from_dict(d)
        assert restored.enabled is False


class TestInstrumentState:
    """Test InstrumentState."""

    def _make_state(self) -> InstrumentState:
        return InstrumentState(
            frequency=FrequencyState(1e9, 100e6, 950e6, 1050e6),
            amplitude=AmplitudeState(0.0, 10.0, False),
            bandwidth=BandwidthState(1e3, 3e3, 0.5),
            markers=[
                MarkerState(1, True, 1e9, -50.0),
                MarkerState(2, False),
            ],
            trace_mode="WRITe",
            detector_type="RMS",
            averaging_count=1,
        )

    def test_to_dict_roundtrip(self):
        state = self._make_state()
        d = state.to_dict()
        restored = InstrumentState.from_dict(d)
        assert restored.frequency.center_frequency_hz == 1e9
        assert restored.amplitude.reference_level_dbm == 0.0
        assert len(restored.markers) == 2

    def test_save_load_roundtrip(self):
        state = self._make_state()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            state.save(filepath)
            loaded = InstrumentState.load(filepath)
            assert loaded.frequency.center_frequency_hz == 1e9
            assert loaded.bandwidth.rbw_hz == 1e3
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_get_summary(self):
        state = self._make_state()
        summary = state.get_summary()
        assert summary["frequency_range"]["center_hz"] == 1e9
        assert summary["rbw_hz"] == 1e3
        assert summary["active_markers"] == 1


class TestStateManager:
    """Test StateManager."""

    def test_list_saved_states_empty_dir(self):
        mgr = StateManager(state_directory="/tmp/nonexistent_sa_states_test")
        states = mgr.list_saved_states()
        assert states == []

    def test_list_saved_states(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = StateManager(state_directory=tmpdir)

            # Save a state file
            state = InstrumentState(
                frequency=FrequencyState(1e9, 100e6, 950e6, 1050e6),
                amplitude=AmplitudeState(0.0, 10.0, False),
                bandwidth=BandwidthState(1e3, 3e3, 0.5),
            )
            state.save(Path(tmpdir) / "test.json")

            states = mgr.list_saved_states()
            assert len(states) == 1
            assert states[0]["filename"] == "test.json"


def _make_mock_sa():
    """Create a mock spectrum analyzer driver for state tests."""
    sa = AsyncMock()
    sa.info = MagicMock()
    sa.info.to_dict.return_value = {"model": "FSW26", "serial_number": "123456"}

    # Default SCPI query responses for capture_state
    query_responses = {
        "SENS:FREQ:CENT?": "1000000000",
        "SENS:FREQ:SPAN?": "100000000",
        "SENS:FREQ:STAR?": "950000000",
        "SENS:FREQ:STOP?": "1050000000",
        "DISP:TRAC:Y:RLEV?": "0",
        "INP:ATT?": "10",
        "INP:GAIN:STAT?": "0",
        "SENS:BAND:RES?": "1000",
        "SENS:BAND:VID?": "3000",
        "SENS:SWE:TIME?": "0.5",
        "CALC:MARK1:X?": "1000000000",
        "CALC:MARK1:Y?": "-50",
        "CALC:MARK2:X?": "ERROR",
        "CALC:MARK2:Y?": "ERROR",
        "CALC:MARK3:X?": "ERROR",
        "CALC:MARK3:Y?": "ERROR",
        "CALC:MARK4:X?": "ERROR",
        "CALC:MARK4:Y?": "ERROR",
    }

    def mock_query(cmd):
        resp = query_responses.get(cmd)
        if resp == "ERROR":
            raise CommunicationError("Marker not available", "test:5025")
        if resp is not None:
            return resp
        return "0"

    sa.scpi_query = AsyncMock(side_effect=mock_query)
    sa.scpi_send = AsyncMock()
    return sa


class TestStateManagerRestore:
    """Test StateManager.restore_state and _apply_state."""

    @pytest.mark.asyncio
    async def test_restore_state_success(self):
        """Successful restore should not raise."""
        mgr = StateManager()
        sa = _make_mock_sa()
        target_state = InstrumentState(
            frequency=FrequencyState(2e9, 200e6, 1.9e9, 2.1e9),
            amplitude=AmplitudeState(-10.0, 20.0, True),
            bandwidth=BandwidthState(10e3, 30e3, 1.0),
            markers=[MarkerState(1, True, 2e9, -40.0)],
            trace_mode="MAXHold",
            averaging_count=10,
        )
        await mgr.restore_state(sa, target_state)
        # Verify SCPI commands were sent
        assert sa.scpi_send.call_count > 0

    @pytest.mark.asyncio
    async def test_restore_state_rollback_on_failure(self):
        """Issue 17: If restore fails, rollback to pre-restore state."""
        mgr = StateManager()
        sa = _make_mock_sa()

        # Track whether we are in the first restore attempt vs rollback.
        # The first _apply_state call (restore) should fail partway through,
        # but the second _apply_state call (rollback) should succeed.
        apply_attempt = 0
        call_count_in_attempt = 0

        async def fail_on_first_attempt(*args, **kwargs):
            nonlocal apply_attempt, call_count_in_attempt
            call_count_in_attempt += 1
            # Fail mid-way through the first attempt (the restore)
            if apply_attempt == 0 and call_count_in_attempt > 3:
                apply_attempt = 1  # Next calls are rollback
                call_count_in_attempt = 0
                raise CommunicationError("Simulated mid-restore failure", "test:5025")
            # Succeed on rollback (apply_attempt >= 1)

        sa.scpi_send = AsyncMock(side_effect=fail_on_first_attempt)

        target_state = InstrumentState(
            frequency=FrequencyState(2e9, 200e6, 1.9e9, 2.1e9),
            amplitude=AmplitudeState(-10.0, 20.0, True),
            bandwidth=BandwidthState(10e3, 30e3, 1.0),
        )

        with pytest.raises(SpectrumAnalyzerError, match="rollback.*succeeded"):
            await mgr.restore_state(sa, target_state)

    @pytest.mark.asyncio
    async def test_restore_state_rollback_also_fails(self):
        """Issue 17: If both restore and rollback fail, error message says so."""
        mgr = StateManager()
        sa = _make_mock_sa()

        # Make scpi_send always fail (both restore and rollback will fail)
        sa.scpi_send = AsyncMock(
            side_effect=CommunicationError("All SCPI commands fail", "test:5025")
        )

        target_state = InstrumentState(
            frequency=FrequencyState(2e9, 200e6, 1.9e9, 2.1e9),
            amplitude=AmplitudeState(-10.0, 20.0, True),
            bandwidth=BandwidthState(10e3, 30e3, 1.0),
        )

        with pytest.raises(SpectrumAnalyzerError, match="rollback also failed"):
            await mgr.restore_state(sa, target_state)

    @pytest.mark.asyncio
    async def test_restore_state_capture_fails(self):
        """Issue 17: If pre-restore capture fails, error says cannot restore."""
        mgr = StateManager()
        sa = AsyncMock()
        sa.info = None
        # Make capture_state fail by making scpi_query fail
        sa.scpi_query = AsyncMock(side_effect=CommunicationError("Cannot query", "test:5025"))

        target_state = InstrumentState(
            frequency=FrequencyState(2e9, 200e6, 1.9e9, 2.1e9),
            amplitude=AmplitudeState(-10.0, 20.0, True),
            bandwidth=BandwidthState(10e3, 30e3, 1.0),
        )

        with pytest.raises(SpectrumAnalyzerError, match="failed to capture current state"):
            await mgr.restore_state(sa, target_state)

    @pytest.mark.asyncio
    async def test_apply_state_sends_correct_scpi(self):
        """Verify _apply_state sends the correct SCPI commands."""
        mgr = StateManager()
        sa = AsyncMock()
        sa.scpi_send = AsyncMock()

        state = InstrumentState(
            frequency=FrequencyState(1e9, 100e6, 950e6, 1050e6),
            amplitude=AmplitudeState(0.0, 10.0, False),
            bandwidth=BandwidthState(1e3, 3e3, 0.5),
            markers=[
                MarkerState(1, True, 1e9, -50.0),
                MarkerState(2, False),
            ],
            trace_mode="WRITe",
            averaging_count=1,
        )

        await mgr._apply_state(sa, state)

        # Collect all sent commands
        sent_cmds = [call.args[0] for call in sa.scpi_send.call_args_list]

        # Check frequency commands
        assert "SENS:FREQ:CENT 1000000000.0" in sent_cmds
        assert "SENS:FREQ:SPAN 100000000.0" in sent_cmds

        # Check amplitude commands
        assert "DISP:TRAC:Y:RLEV 0.0" in sent_cmds
        assert "INP:ATT 10.0" in sent_cmds
        assert "INP:GAIN:STAT OFF" in sent_cmds

        # Check bandwidth commands
        assert "SENS:BAND:RES 1000.0" in sent_cmds
        assert "SENS:BAND:VID 3000.0" in sent_cmds
        assert "SENS:SWE:TIME 0.5" in sent_cmds

        # Check trace mode
        assert "DISP:TRAC1:MODE WRITe" in sent_cmds

        # Check averaging (off for count=1)
        assert "SENS:AVER:STAT OFF" in sent_cmds

        # Check markers
        assert "CALC:MARK1:STAT ON" in sent_cmds
        assert "CALC:MARK1:X 1000000000.0" in sent_cmds
        assert "CALC:MARK2:STAT OFF" in sent_cmds
