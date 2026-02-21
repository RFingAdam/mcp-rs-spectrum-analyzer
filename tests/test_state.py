"""Tests for state management."""

import tempfile
from pathlib import Path

from rs_spectrum_analyzer_mcp.state import (
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
