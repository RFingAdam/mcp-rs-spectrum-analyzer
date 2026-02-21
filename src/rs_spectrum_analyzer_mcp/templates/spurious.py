"""Spurious emission measurement template."""

from dataclasses import dataclass, field
from typing import Any

from .base import MeasurementTemplate, SAConfig


@dataclass
class SpuriousEmissionTemplate(MeasurementTemplate):
    """
    Spurious emission measurement template.

    Configures the spectrum analyzer for wideband spurious emission
    scanning with limit lines for compliance testing.
    """

    scan_ranges: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = super().to_dict()
        d["scan_ranges"] = self.scan_ranges
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpuriousEmissionTemplate":
        """Create from dictionary."""
        config = SAConfig.from_dict(data["config"])
        return cls(
            name=data["name"],
            description=data["description"],
            config=config,
            metadata=data.get("metadata", {}),
            scan_ranges=data.get("scan_ranges", []),
        )

    @classmethod
    def wideband_spurious(
        cls,
        center_frequency_hz: float = 1e9,
        span_hz: float = 3e9,
    ) -> "SpuriousEmissionTemplate":
        """
        Create wideband spurious emission scan template.

        Args:
            center_frequency_hz: Center frequency of scan
            span_hz: Total scan span
        """
        return cls(
            name="Wideband Spurious Scan",
            description=(
                f"Wideband spurious emission scan centered at "
                f"{center_frequency_hz / 1e9:.1f} GHz with {span_hz / 1e9:.1f} GHz span"
            ),
            config=SAConfig(
                center_frequency_hz=center_frequency_hz,
                span_hz=span_hz,
                rbw_hz=1e6,  # Wide RBW for fast scan
                vbw_hz=3e6,
                reference_level_dbm=0.0,
                detector_type="POS",  # Peak detector for spurious
                trace_mode="MAXHold",
                averaging_count=1,
            ),
            scan_ranges=[
                {
                    "name": "Full span",
                    "start_hz": center_frequency_hz - span_hz / 2,
                    "stop_hz": center_frequency_hz + span_hz / 2,
                    "rbw_hz": 1e6,
                }
            ],
        )

    @classmethod
    def harmonic_spurious(
        cls,
        fundamental_hz: float = 1e9,
        num_harmonics: int = 5,
    ) -> "SpuriousEmissionTemplate":
        """
        Create harmonic spurious scan template.

        Covers from DC to N * fundamental frequency.
        """
        max_freq = fundamental_hz * (num_harmonics + 0.5)
        return cls(
            name=f"Harmonic Spurious ({num_harmonics} harmonics)",
            description=(
                f"Spurious scan for {num_harmonics} harmonics of "
                f"{fundamental_hz / 1e6:.1f} MHz fundamental"
            ),
            config=SAConfig(
                center_frequency_hz=max_freq / 2,
                span_hz=max_freq,
                rbw_hz=100e3,
                vbw_hz=300e3,
                reference_level_dbm=10.0,
                detector_type="POS",
                trace_mode="MAXHold",
                averaging_count=1,
            ),
            scan_ranges=[
                {
                    "name": f"Harmonic {n}",
                    "center_hz": fundamental_hz * n,
                    "span_hz": fundamental_hz * 0.1,
                }
                for n in range(1, num_harmonics + 1)
            ],
        )
