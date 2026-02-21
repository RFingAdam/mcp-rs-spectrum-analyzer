"""Spectrum analyzer type definitions and data models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpectrumAnalyzerFamily(Enum):
    """
    Rohde & Schwarz spectrum/signal analyzer product families.

    Each family has different capabilities and frequency ranges.
    """

    FSW = "FSW"  # High-end signal and spectrum analyzer (up to 90 GHz)
    FSVA3000 = "FSVA3000"  # Mid-range high performance
    FSV3000 = "FSV3000"  # Mid-range workhorse
    FPL1000 = "FPL1000"  # Entry-level (up to 40 GHz)

    @property
    def max_frequency_hz(self) -> float:
        """Maximum frequency for this family."""
        freq_map = {
            SpectrumAnalyzerFamily.FSW: 90e9,
            SpectrumAnalyzerFamily.FSVA3000: 44e9,
            SpectrumAnalyzerFamily.FSV3000: 44e9,
            SpectrumAnalyzerFamily.FPL1000: 40e9,
        }
        return freq_map[self]

    @property
    def min_frequency_hz(self) -> float:
        """Minimum frequency for this family."""
        freq_map = {
            SpectrumAnalyzerFamily.FSW: 2.0,
            SpectrumAnalyzerFamily.FSVA3000: 10.0,
            SpectrumAnalyzerFamily.FSV3000: 10.0,
            SpectrumAnalyzerFamily.FPL1000: 5e3,
        }
        return freq_map[self]

    @property
    def has_preamp(self) -> bool:
        """Whether this family has a built-in preamplifier."""
        return True  # All supported models have preamp option


class TraceMode(Enum):
    """Trace display modes."""

    WRITE = "WRITe"  # Clear/write (normal)
    MAX_HOLD = "MAXHold"  # Maximum hold
    MIN_HOLD = "MINHold"  # Minimum hold
    AVERAGE = "AVERage"  # Trace averaging


class DetectorType(Enum):
    """Detector types for spectrum analysis."""

    PEAK = "POS"  # Positive peak
    RMS = "RMS"  # RMS
    AVERAGE = "AVER"  # Average (voltage)
    SAMPLE = "SAMP"  # Sample
    QUASI_PEAK = "QPE"  # Quasi-peak (EMI)
    NEGATIVE_PEAK = "NEG"  # Negative peak
    CISPR_AVERAGE = "CAV"  # CISPR average (EMI)


class TriggerSource(Enum):
    """Trigger sources for sweep control."""

    FREE_RUN = "IMM"  # Free run (immediate)
    EXTERNAL = "EXT"  # External trigger
    VIDEO = "VID"  # Video trigger
    IF_POWER = "IFP"  # IF power trigger
    RF_POWER = "RFP"  # RF power trigger


@dataclass
class InstrumentInfo:
    """Instrument identification information from *IDN? response."""

    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "firmware_version": self.firmware_version,
        }

    @classmethod
    def from_idn(cls, idn_string: str) -> "InstrumentInfo":
        """
        Parse *IDN? response string.

        R&S format: Rohde&Schwarz,FSW-26,1312.8000K26/100xxxx,x.xx.x.xx

        Args:
            idn_string: Raw *IDN? response

        Returns:
            InstrumentInfo instance
        """
        parts = idn_string.strip().split(",")
        if len(parts) >= 4:
            return cls(
                manufacturer=parts[0].strip(),
                model=parts[1].strip(),
                serial_number=parts[2].strip(),
                firmware_version=parts[3].strip(),
            )
        return cls(
            manufacturer=parts[0].strip() if parts else "Unknown",
            model=parts[1].strip() if len(parts) > 1 else "Unknown",
            serial_number=parts[2].strip() if len(parts) > 2 else "Unknown",
            firmware_version=parts[3].strip() if len(parts) > 3 else "Unknown",
        )

    def detect_family(self) -> SpectrumAnalyzerFamily | None:
        """Detect instrument family from model string."""
        model_upper = self.model.upper()
        if "FSW" in model_upper:
            return SpectrumAnalyzerFamily.FSW
        elif "FSVA" in model_upper:
            return SpectrumAnalyzerFamily.FSVA3000
        elif "FSV" in model_upper:
            return SpectrumAnalyzerFamily.FSV3000
        elif "FPL" in model_upper:
            return SpectrumAnalyzerFamily.FPL1000
        return None


@dataclass
class TraceData:
    """Trace data from the spectrum analyzer."""

    frequencies: list[float]
    amplitudes: list[float]  # in dBm typically
    trace_number: int = 1
    detector_type: str = "RMS"
    rbw_hz: float | None = None
    vbw_hz: float | None = None
    sweep_time_s: float | None = None
    reference_level_dbm: float | None = None

    @property
    def num_points(self) -> int:
        """Number of trace points."""
        return len(self.frequencies)

    @property
    def peak_amplitude(self) -> float:
        """Maximum amplitude in trace."""
        return max(self.amplitudes) if self.amplitudes else float("-inf")

    @property
    def peak_frequency(self) -> float:
        """Frequency at peak amplitude."""
        if not self.amplitudes:
            return 0.0
        idx = self.amplitudes.index(max(self.amplitudes))
        return self.frequencies[idx]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_number": self.trace_number,
            "num_points": self.num_points,
            "frequencies": self.frequencies,
            "amplitudes": self.amplitudes,
            "detector_type": self.detector_type,
            "rbw_hz": self.rbw_hz,
            "vbw_hz": self.vbw_hz,
            "sweep_time_s": self.sweep_time_s,
            "reference_level_dbm": self.reference_level_dbm,
            "peak_amplitude_dbm": self.peak_amplitude,
            "peak_frequency_hz": self.peak_frequency,
        }

    def to_summary(self) -> dict[str, Any]:
        """Convert to summary (without raw data arrays)."""
        return {
            "trace_number": self.trace_number,
            "num_points": self.num_points,
            "start_freq_hz": self.frequencies[0] if self.frequencies else None,
            "stop_freq_hz": self.frequencies[-1] if self.frequencies else None,
            "detector_type": self.detector_type,
            "rbw_hz": self.rbw_hz,
            "vbw_hz": self.vbw_hz,
            "sweep_time_s": self.sweep_time_s,
            "reference_level_dbm": self.reference_level_dbm,
            "peak_amplitude_dbm": self.peak_amplitude,
            "peak_frequency_hz": self.peak_frequency,
        }


@dataclass
class MarkerData:
    """Marker measurement result."""

    marker_number: int
    frequency_hz: float
    amplitude_dbm: float
    delta_mode: bool = False
    delta_frequency_hz: float | None = None
    delta_amplitude_db: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "marker_number": self.marker_number,
            "frequency_hz": self.frequency_hz,
            "amplitude_dbm": self.amplitude_dbm,
            "delta_mode": self.delta_mode,
        }
        if self.delta_mode:
            result["delta_frequency_hz"] = self.delta_frequency_hz
            result["delta_amplitude_db"] = self.delta_amplitude_db
        return result


@dataclass
class ChannelPowerResult:
    """Channel power measurement result."""

    channel_power_dbm: float
    channel_power_density_dbm_hz: float
    channel_bandwidth_hz: float
    center_frequency_hz: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "channel_power_dbm": self.channel_power_dbm,
            "channel_power_density_dbm_hz": self.channel_power_density_dbm_hz,
            "channel_bandwidth_hz": self.channel_bandwidth_hz,
            "center_frequency_hz": self.center_frequency_hz,
        }


@dataclass
class ACLRResult:
    """Adjacent channel leakage ratio measurement result."""

    channel_power_dbm: float
    lower_adjacent_dbm: float
    upper_adjacent_dbm: float
    lower_aclr_db: float
    upper_aclr_db: float
    lower_alternate_dbm: float | None = None
    upper_alternate_dbm: float | None = None
    lower_alternate_aclr_db: float | None = None
    upper_alternate_aclr_db: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "channel_power_dbm": self.channel_power_dbm,
            "lower_adjacent_dbm": self.lower_adjacent_dbm,
            "upper_adjacent_dbm": self.upper_adjacent_dbm,
            "lower_aclr_db": self.lower_aclr_db,
            "upper_aclr_db": self.upper_aclr_db,
        }
        if self.lower_alternate_dbm is not None:
            result["lower_alternate_dbm"] = self.lower_alternate_dbm
            result["upper_alternate_dbm"] = self.upper_alternate_dbm
            result["lower_alternate_aclr_db"] = self.lower_alternate_aclr_db
            result["upper_alternate_aclr_db"] = self.upper_alternate_aclr_db
        return result


@dataclass
class SEMResult:
    """Spectrum emission mask result."""

    passed: bool
    tx_power_dbm: float
    violations: list[dict[str, Any]] = field(default_factory=list)
    num_ranges: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "tx_power_dbm": self.tx_power_dbm,
            "violations": self.violations,
            "num_ranges": self.num_ranges,
        }


@dataclass
class OBWResult:
    """Occupied bandwidth measurement result."""

    occupied_bandwidth_hz: float
    center_frequency_hz: float
    power_percentage: float = 99.0  # Typically 99% power bandwidth
    lower_frequency_hz: float | None = None
    upper_frequency_hz: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "occupied_bandwidth_hz": self.occupied_bandwidth_hz,
            "center_frequency_hz": self.center_frequency_hz,
            "power_percentage": self.power_percentage,
            "lower_frequency_hz": self.lower_frequency_hz,
            "upper_frequency_hz": self.upper_frequency_hz,
        }


@dataclass
class BandwidthResult:
    """N-dB bandwidth measurement result."""

    bandwidth_hz: float
    center_frequency_hz: float
    n_db: float = 3.0
    lower_frequency_hz: float | None = None
    upper_frequency_hz: float | None = None
    quality_factor: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "bandwidth_hz": self.bandwidth_hz,
            "center_frequency_hz": self.center_frequency_hz,
            "n_db": self.n_db,
        }
        if self.lower_frequency_hz is not None:
            result["lower_frequency_hz"] = self.lower_frequency_hz
        if self.upper_frequency_hz is not None:
            result["upper_frequency_hz"] = self.upper_frequency_hz
        if self.quality_factor is not None:
            result["quality_factor"] = self.quality_factor
        return result
