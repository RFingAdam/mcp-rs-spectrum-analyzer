"""EMI precompliance measurement template."""

from dataclasses import dataclass, field
from typing import Any

from .base import MeasurementTemplate, SAConfig


@dataclass
class EMIPrecomplianceTemplate(MeasurementTemplate):
    """
    EMI precompliance measurement template.

    Configures the spectrum analyzer for EMI precompliance testing
    with CISPR-compliant bandwidths, quasi-peak detection, and
    appropriate scan parameters.
    """

    standard: str = "CISPR 32"
    emission_class: str = "B"  # A or B
    detector_types: list[str] = field(default_factory=lambda: ["QPE", "AVER"])
    dwell_time_s: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = super().to_dict()
        d["standard"] = self.standard
        d["emission_class"] = self.emission_class
        d["detector_types"] = self.detector_types
        d["dwell_time_s"] = self.dwell_time_s
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EMIPrecomplianceTemplate":
        """Create from dictionary."""
        config = SAConfig.from_dict(data["config"])
        return cls(
            name=data["name"],
            description=data["description"],
            config=config,
            metadata=data.get("metadata", {}),
            standard=data.get("standard", "CISPR 32"),
            emission_class=data.get("emission_class", "B"),
            detector_types=data.get("detector_types", ["QPE", "AVER"]),
            dwell_time_s=data.get("dwell_time_s", 1.0),
        )

    @classmethod
    def cispr_32_class_b(cls) -> "EMIPrecomplianceTemplate":
        """
        Create CISPR 32 Class B conducted emissions template.

        Band A: 150 kHz - 500 kHz, RBW 200 Hz (CISPR Band A)
        Band B: 150 kHz - 30 MHz, RBW 9 kHz (CISPR Band B)

        This configures for Band B (most common for conducted emissions).
        Quasi-peak + average detectors per CISPR 32 requirements.
        """
        return cls(
            name="CISPR 32 Class B Conducted",
            description=(
                "Conducted emissions precompliance per CISPR 32 Class B. "
                "Band B: 150 kHz - 30 MHz, 9 kHz CISPR RBW, QP + AVG detectors."
            ),
            config=SAConfig(
                center_frequency_hz=15.075e6,  # Center of 150 kHz - 30 MHz
                span_hz=29.85e6,  # 30 MHz - 150 kHz
                rbw_hz=9e3,  # CISPR Band B RBW
                vbw_hz=30e3,  # VBW >= 3x RBW for EMI
                reference_level_dbm=10.0,
                detector_type="QPE",  # Quasi-peak primary
                trace_mode="MAXHold",  # Max hold for emissions
                averaging_count=1,
                preamp_enabled=True,
            ),
            standard="CISPR 32",
            emission_class="B",
            detector_types=["QPE", "AVER"],
            dwell_time_s=1.0,
            metadata={
                "frequency_range": "150 kHz - 30 MHz",
                "cispr_band": "B",
                "limit_standard": "CISPR 32 Class B",
                "quasi_peak_limit_dbm": {
                    "150kHz-500kHz": "56-46 dBuV (sliding)",
                    "500kHz-5MHz": "46 dBuV",
                    "5MHz-30MHz": "50 dBuV",
                },
                "average_limit_dbm": {
                    "150kHz-500kHz": "46-36 dBuV (sliding)",
                    "500kHz-5MHz": "36 dBuV",
                    "5MHz-30MHz": "40 dBuV",
                },
            },
        )

    @classmethod
    def cispr_32_class_b_radiated(cls) -> "EMIPrecomplianceTemplate":
        """Create CISPR 32 Class B radiated emissions template (30 MHz - 1 GHz)."""
        return cls(
            name="CISPR 32 Class B Radiated (30 MHz - 1 GHz)",
            description=(
                "Radiated emissions precompliance per CISPR 32 Class B. "
                "Band C/D: 30 MHz - 1 GHz, 120 kHz CISPR RBW, QP detector."
            ),
            config=SAConfig(
                center_frequency_hz=515e6,
                span_hz=970e6,
                rbw_hz=120e3,  # CISPR Band C/D RBW
                vbw_hz=360e3,
                reference_level_dbm=10.0,
                detector_type="QPE",
                trace_mode="MAXHold",
                averaging_count=1,
                preamp_enabled=True,
            ),
            standard="CISPR 32",
            emission_class="B",
            detector_types=["QPE", "AVER"],
            dwell_time_s=1.0,
            metadata={
                "frequency_range": "30 MHz - 1 GHz",
                "cispr_band": "C/D",
            },
        )
