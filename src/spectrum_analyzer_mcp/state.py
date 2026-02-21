"""Instrument state management for spectrum analyzer configuration persistence."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .exceptions import SpectrumAnalyzerError

logger = logging.getLogger(__name__)


@dataclass
class FrequencyState:
    """State of frequency configuration."""

    center_frequency_hz: float
    span_hz: float
    start_frequency_hz: float
    stop_frequency_hz: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "center_frequency_hz": self.center_frequency_hz,
            "span_hz": self.span_hz,
            "start_frequency_hz": self.start_frequency_hz,
            "stop_frequency_hz": self.stop_frequency_hz,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FrequencyState":
        """Create from dictionary."""
        return cls(
            center_frequency_hz=data["center_frequency_hz"],
            span_hz=data["span_hz"],
            start_frequency_hz=data["start_frequency_hz"],
            stop_frequency_hz=data["stop_frequency_hz"],
        )


@dataclass
class AmplitudeState:
    """State of amplitude configuration."""

    reference_level_dbm: float
    attenuation_db: float
    preamp_enabled: bool
    scale_db_per_div: float = 10.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "reference_level_dbm": self.reference_level_dbm,
            "attenuation_db": self.attenuation_db,
            "preamp_enabled": self.preamp_enabled,
            "scale_db_per_div": self.scale_db_per_div,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AmplitudeState":
        """Create from dictionary."""
        return cls(
            reference_level_dbm=data["reference_level_dbm"],
            attenuation_db=data["attenuation_db"],
            preamp_enabled=data.get("preamp_enabled", False),
            scale_db_per_div=data.get("scale_db_per_div", 10.0),
        )


@dataclass
class BandwidthState:
    """State of bandwidth configuration."""

    rbw_hz: float
    vbw_hz: float
    sweep_time_s: float
    rbw_auto: bool = True
    vbw_auto: bool = True
    sweep_time_auto: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rbw_hz": self.rbw_hz,
            "vbw_hz": self.vbw_hz,
            "sweep_time_s": self.sweep_time_s,
            "rbw_auto": self.rbw_auto,
            "vbw_auto": self.vbw_auto,
            "sweep_time_auto": self.sweep_time_auto,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BandwidthState":
        """Create from dictionary."""
        return cls(
            rbw_hz=data["rbw_hz"],
            vbw_hz=data["vbw_hz"],
            sweep_time_s=data["sweep_time_s"],
            rbw_auto=data.get("rbw_auto", True),
            vbw_auto=data.get("vbw_auto", True),
            sweep_time_auto=data.get("sweep_time_auto", True),
        )


@dataclass
class MarkerState:
    """State of a spectrum analyzer marker."""

    marker_number: int
    enabled: bool
    frequency_hz: float | None = None
    amplitude_dbm: float | None = None
    delta_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "marker_number": self.marker_number,
            "enabled": self.enabled,
            "frequency_hz": self.frequency_hz,
            "amplitude_dbm": self.amplitude_dbm,
            "delta_mode": self.delta_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarkerState":
        """Create from dictionary."""
        return cls(
            marker_number=data["marker_number"],
            enabled=data.get("enabled", False),
            frequency_hz=data.get("frequency_hz"),
            amplitude_dbm=data.get("amplitude_dbm"),
            delta_mode=data.get("delta_mode", False),
        )


@dataclass
class InstrumentState:
    """
    Complete spectrum analyzer configuration state.

    Captures all relevant SA settings that can be saved and restored,
    enabling reproducible measurements and configuration management.
    """

    frequency: FrequencyState
    amplitude: AmplitudeState
    bandwidth: BandwidthState
    markers: list[MarkerState] = field(default_factory=list)
    trace_mode: str = "WRITe"
    detector_type: str = "RMS"
    averaging_count: int = 1
    continuous_sweep: bool = True
    timestamp: datetime = field(default_factory=datetime.now)
    instrument_info: dict[str, str] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "frequency": self.frequency.to_dict(),
            "amplitude": self.amplitude.to_dict(),
            "bandwidth": self.bandwidth.to_dict(),
            "markers": [m.to_dict() for m in self.markers],
            "trace_mode": self.trace_mode,
            "detector_type": self.detector_type,
            "averaging_count": self.averaging_count,
            "continuous_sweep": self.continuous_sweep,
            "timestamp": self.timestamp.isoformat(),
            "instrument_info": self.instrument_info,
            "notes": self.notes,
            "version": "1.0",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstrumentState":
        """Create state from dictionary."""
        frequency = FrequencyState.from_dict(data["frequency"])
        amplitude = AmplitudeState.from_dict(data["amplitude"])
        bandwidth = BandwidthState.from_dict(data["bandwidth"])

        markers = []
        if data.get("markers"):
            markers = [MarkerState.from_dict(m) for m in data["markers"]]

        timestamp = datetime.now()
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except ValueError:
                logger.debug(
                    "Could not parse timestamp '%s', using current time",
                    data["timestamp"],
                )

        return cls(
            frequency=frequency,
            amplitude=amplitude,
            bandwidth=bandwidth,
            markers=markers,
            trace_mode=data.get("trace_mode", "WRITe"),
            detector_type=data.get("detector_type", "RMS"),
            averaging_count=data.get("averaging_count", 1),
            continuous_sweep=data.get("continuous_sweep", True),
            timestamp=timestamp,
            instrument_info=data.get("instrument_info", {}),
            notes=data.get("notes", ""),
        )

    def save(self, filepath: str | Path) -> None:
        """Save state to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str | Path) -> "InstrumentState":
        """Load state from JSON file."""
        filepath = Path(filepath)

        with open(filepath) as f:
            data = json.load(f)

        return cls.from_dict(data)

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the state."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "frequency_range": {
                "center_hz": self.frequency.center_frequency_hz,
                "span_hz": self.frequency.span_hz,
                "start_hz": self.frequency.start_frequency_hz,
                "stop_hz": self.frequency.stop_frequency_hz,
            },
            "reference_level_dbm": self.amplitude.reference_level_dbm,
            "attenuation_db": self.amplitude.attenuation_db,
            "rbw_hz": self.bandwidth.rbw_hz,
            "vbw_hz": self.bandwidth.vbw_hz,
            "trace_mode": self.trace_mode,
            "detector_type": self.detector_type,
            "active_markers": sum(1 for m in self.markers if m.enabled),
            "instrument": self.instrument_info.get("model", "Unknown"),
        }


class StateManager:
    """
    Manages spectrum analyzer state capture and restoration.

    Provides methods to capture current SA state, save/load state files,
    and restore state to SA.
    """

    def __init__(self, state_directory: str | Path | None = None):
        """
        Initialize state manager.

        Args:
            state_directory: Directory for state files (default: ./sa_states)
        """
        if state_directory is None:
            state_directory = Path("./sa_states")
        self.state_directory = Path(state_directory)

    async def capture_state(self, sa) -> InstrumentState:
        """
        Capture current spectrum analyzer state.

        Args:
            sa: RSSpectrumAnalyzerDriver instance

        Returns:
            Captured InstrumentState
        """
        # Query frequency state
        center = await sa.scpi_query("SENS:FREQ:CENT?")
        span = await sa.scpi_query("SENS:FREQ:SPAN?")
        start = await sa.scpi_query("SENS:FREQ:STAR?")
        stop = await sa.scpi_query("SENS:FREQ:STOP?")

        frequency = FrequencyState(
            center_frequency_hz=float(center),
            span_hz=float(span),
            start_frequency_hz=float(start),
            stop_frequency_hz=float(stop),
        )

        # Query amplitude state
        ref_level = await sa.scpi_query("DISP:TRAC:Y:RLEV?")
        attenuation = await sa.scpi_query("INP:ATT?")
        try:
            preamp = await sa.scpi_query("INP:GAIN:STAT?")
            preamp_on = preamp.strip() in ("1", "ON")
        except (SpectrumAnalyzerError, ValueError) as e:
            logger.debug("Could not query preamp state, assuming off: %s", e)
            preamp_on = False

        amplitude = AmplitudeState(
            reference_level_dbm=float(ref_level),
            attenuation_db=float(attenuation),
            preamp_enabled=preamp_on,
        )

        # Query bandwidth state
        rbw = await sa.scpi_query("SENS:BAND:RES?")
        vbw = await sa.scpi_query("SENS:BAND:VID?")
        swt = await sa.scpi_query("SENS:SWE:TIME?")

        bandwidth = BandwidthState(
            rbw_hz=float(rbw),
            vbw_hz=float(vbw),
            sweep_time_s=float(swt),
        )

        # Get instrument info
        instrument_info = {}
        if sa.info:
            instrument_info = sa.info.to_dict()

        # Capture marker states
        markers = []
        for i in range(1, 5):
            try:
                freq = await sa.scpi_query(f"CALC:MARK{i}:X?")
                amp = await sa.scpi_query(f"CALC:MARK{i}:Y?")
                markers.append(
                    MarkerState(
                        marker_number=i,
                        enabled=True,
                        frequency_hz=float(freq),
                        amplitude_dbm=float(amp),
                    )
                )
            except (SpectrumAnalyzerError, ValueError) as e:
                logger.debug("Marker %d not active or could not be read: %s", i, e)
                markers.append(
                    MarkerState(
                        marker_number=i,
                        enabled=False,
                    )
                )

        return InstrumentState(
            frequency=frequency,
            amplitude=amplitude,
            bandwidth=bandwidth,
            markers=markers,
            instrument_info=instrument_info,
        )

    async def restore_state(self, sa, state: InstrumentState) -> None:
        """
        Restore spectrum analyzer to saved state with rollback on failure.

        Captures the current instrument state before attempting restore.
        If restore fails partway through, rolls back to the pre-restore state
        so the instrument is not left in an inconsistent configuration.

        Args:
            sa: RSSpectrumAnalyzerDriver instance
            state: State to restore

        Raises:
            SpectrumAnalyzerError: If restore fails (rollback will be attempted)
        """
        # Issue 17: Capture pre-restore state snapshot for rollback
        logger.info("Capturing pre-restore state snapshot for rollback safety")
        try:
            pre_restore_state = await self.capture_state(sa)
        except (SpectrumAnalyzerError, ValueError) as e:
            logger.error("Failed to capture pre-restore state: %s", e)
            raise SpectrumAnalyzerError(
                f"Cannot restore state: failed to capture current state for rollback: {e}"
            )

        try:
            await self._apply_state(sa, state)
            logger.info("State restored successfully")
        except (SpectrumAnalyzerError, ValueError, OSError) as restore_err:
            logger.error(
                "State restore failed at: %s. Attempting rollback to pre-restore state.",
                restore_err,
            )
            try:
                await self._apply_state(sa, pre_restore_state)
                logger.info("Rollback to pre-restore state succeeded")
            except (SpectrumAnalyzerError, ValueError, OSError) as rollback_err:
                logger.error(
                    "Rollback also failed: %s. Instrument may be in inconsistent state.",
                    rollback_err,
                )
                raise SpectrumAnalyzerError(
                    f"State restore failed ({restore_err}) and rollback also failed "
                    f"({rollback_err}). Instrument may be in inconsistent state. "
                    f"Consider using *RST to reset the instrument."
                )
            raise SpectrumAnalyzerError(
                f"State restore failed ({restore_err}), but rollback to "
                f"pre-restore state succeeded."
            )

    async def _apply_state(self, sa, state: InstrumentState) -> None:
        """
        Apply instrument state settings via SCPI commands.

        This is the internal method that does the actual SCPI writes.
        Used by both restore_state (for the target state) and rollback.

        Args:
            sa: RSSpectrumAnalyzerDriver instance
            state: State to apply

        Raises:
            SpectrumAnalyzerError: If any SCPI command fails
        """
        # Restore frequency
        await sa.scpi_send(f"SENS:FREQ:CENT {state.frequency.center_frequency_hz}")
        await sa.scpi_send(f"SENS:FREQ:SPAN {state.frequency.span_hz}")

        # Restore amplitude
        await sa.scpi_send(f"DISP:TRAC:Y:RLEV {state.amplitude.reference_level_dbm}")
        await sa.scpi_send(f"INP:ATT {state.amplitude.attenuation_db}")
        preamp_state = "ON" if state.amplitude.preamp_enabled else "OFF"
        await sa.scpi_send(f"INP:GAIN:STAT {preamp_state}")

        # Restore bandwidth
        await sa.scpi_send(f"SENS:BAND:RES {state.bandwidth.rbw_hz}")
        await sa.scpi_send(f"SENS:BAND:VID {state.bandwidth.vbw_hz}")
        await sa.scpi_send(f"SENS:SWE:TIME {state.bandwidth.sweep_time_s}")

        # Restore trace mode
        await sa.scpi_send(f"DISP:TRAC1:MODE {state.trace_mode}")

        # Restore averaging
        if state.averaging_count > 1:
            await sa.scpi_send("SENS:AVER:STAT ON")
            await sa.scpi_send(f"SENS:AVER:COUN {state.averaging_count}")
        else:
            await sa.scpi_send("SENS:AVER:STAT OFF")

        # Restore markers
        for marker in state.markers:
            if marker.enabled and marker.frequency_hz is not None:
                await sa.scpi_send(f"CALC:MARK{marker.marker_number}:STAT ON")
                await sa.scpi_send(f"CALC:MARK{marker.marker_number}:X {marker.frequency_hz}")
            else:
                await sa.scpi_send(f"CALC:MARK{marker.marker_number}:STAT OFF")

    def list_saved_states(self) -> list[dict[str, Any]]:
        """List all saved state files."""
        states = []
        if not self.state_directory.exists():
            return states

        for filepath in self.state_directory.glob("*.json"):
            try:
                state = InstrumentState.load(filepath)
                states.append(
                    {
                        "filename": filepath.name,
                        "path": str(filepath),
                        "summary": state.get_summary(),
                    }
                )
            except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
                logger.warning("Failed to load state file %s: %s", filepath, e)
                states.append(
                    {
                        "filename": filepath.name,
                        "path": str(filepath),
                        "error": str(e),
                    }
                )

        return states
