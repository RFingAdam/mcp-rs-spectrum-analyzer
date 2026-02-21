"""Harmonic measurement template."""

from dataclasses import dataclass
from typing import Any

from .base import MeasurementTemplate, SAConfig


@dataclass
class HarmonicTemplate(MeasurementTemplate):
    """
    Harmonic measurement template.

    Configures the spectrum analyzer to measure fundamental + N harmonics,
    reporting power levels and harmonic distortion.
    """

    fundamental_frequency_hz: float = 1e9
    num_harmonics: int = 5
    harmonic_span_hz: float | None = None  # Span around each harmonic

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = super().to_dict()
        d["fundamental_frequency_hz"] = self.fundamental_frequency_hz
        d["num_harmonics"] = self.num_harmonics
        d["harmonic_span_hz"] = self.harmonic_span_hz
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HarmonicTemplate":
        """Create from dictionary."""
        config = SAConfig.from_dict(data["config"])
        return cls(
            name=data["name"],
            description=data["description"],
            config=config,
            metadata=data.get("metadata", {}),
            fundamental_frequency_hz=data.get("fundamental_frequency_hz", 1e9),
            num_harmonics=data.get("num_harmonics", 5),
            harmonic_span_hz=data.get("harmonic_span_hz"),
        )

    @classmethod
    def create(
        cls,
        fundamental_hz: float,
        num_harmonics: int = 5,
        reference_level_dbm: float = 10.0,
    ) -> "HarmonicTemplate":
        """
        Create harmonic measurement template.

        Args:
            fundamental_hz: Fundamental frequency in Hz
            num_harmonics: Number of harmonics to measure (default 5)
            reference_level_dbm: Reference level in dBm
        """
        max_freq = fundamental_hz * (num_harmonics + 0.5)
        span = max_freq

        return cls(
            name=f"Harmonics of {fundamental_hz / 1e6:.1f} MHz",
            description=(
                f"Measure fundamental + {num_harmonics} harmonics of "
                f"{fundamental_hz / 1e6:.3f} MHz"
            ),
            config=SAConfig(
                center_frequency_hz=max_freq / 2,
                span_hz=span,
                rbw_hz=max(fundamental_hz / 1000, 1e3),
                vbw_hz=max(fundamental_hz / 300, 3e3),
                reference_level_dbm=reference_level_dbm,
                detector_type="POS",
                trace_mode="WRITe",
                averaging_count=5,
            ),
            fundamental_frequency_hz=fundamental_hz,
            num_harmonics=num_harmonics,
            harmonic_span_hz=fundamental_hz * 0.05,
            metadata={
                "harmonic_frequencies": [
                    fundamental_hz * n for n in range(1, num_harmonics + 1)
                ],
            },
        )
