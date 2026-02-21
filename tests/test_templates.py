"""Tests for measurement templates."""

import tempfile
from pathlib import Path

from spectrum_analyzer_mcp.templates import (
    ACLRTemplate,
    ChannelPowerTemplate,
    EMIPrecomplianceTemplate,
    HarmonicTemplate,
    MeasurementTemplate,
    OccupiedBandwidthTemplate,
    SpuriousEmissionTemplate,
)
from spectrum_analyzer_mcp.templates.base import SAConfig


class TestSAConfig:
    """Test SAConfig."""

    def test_to_dict_roundtrip(self):
        config = SAConfig(
            center_frequency_hz=1e9,
            span_hz=100e6,
            rbw_hz=1e3,
            vbw_hz=3e3,
            reference_level_dbm=0.0,
        )
        d = config.to_dict()
        restored = SAConfig.from_dict(d)
        assert restored.center_frequency_hz == 1e9
        assert restored.rbw_hz == 1e3


class TestMeasurementTemplate:
    """Test base MeasurementTemplate."""

    def test_get_summary(self):
        config = SAConfig(1e9, 100e6, 1e3, 3e3)
        template = MeasurementTemplate(
            name="Test",
            description="A test template",
            config=config,
        )
        summary = template.get_summary()
        assert summary["name"] == "Test"
        assert summary["center_frequency_hz"] == 1e9

    def test_save_load_roundtrip(self):
        config = SAConfig(1e9, 100e6, 1e3, 3e3)
        template = MeasurementTemplate(
            name="Test",
            description="A test template",
            config=config,
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            template.save(filepath)
            loaded = MeasurementTemplate.load(filepath)
            assert loaded.name == "Test"
            assert loaded.config.center_frequency_hz == 1e9
        finally:
            Path(filepath).unlink(missing_ok=True)


class TestChannelPowerTemplate:
    """Test ChannelPowerTemplate presets."""

    def test_lte_10mhz(self):
        t = ChannelPowerTemplate.lte_10mhz()
        assert t.name == "LTE 10 MHz Channel Power"
        assert t.config.span_hz == 20e6
        assert t.config.rbw_hz == 30e3
        assert t.channel_bandwidth_hz == 9.015e6

    def test_nr_100mhz(self):
        t = ChannelPowerTemplate.nr_100mhz()
        assert t.config.span_hz == 200e6
        assert t.channel_bandwidth_hz == 98.31e6

    def test_wlan_80mhz(self):
        t = ChannelPowerTemplate.wlan_80mhz()
        assert t.channel_bandwidth_hz == 80e6

    def test_custom_center_frequency(self):
        t = ChannelPowerTemplate.lte_10mhz(center_frequency_hz=2.1e9)
        assert t.config.center_frequency_hz == 2.1e9

    def test_to_dict_roundtrip(self):
        t = ChannelPowerTemplate.lte_10mhz()
        d = t.to_dict()
        t2 = ChannelPowerTemplate.from_dict(d)
        assert t2.channel_bandwidth_hz == t.channel_bandwidth_hz


class TestACLRTemplate:
    """Test ACLRTemplate presets."""

    def test_lte_10mhz(self):
        t = ACLRTemplate.lte_10mhz()
        assert t.channel_bandwidth_hz == 9.015e6
        assert t.adjacent_offset_hz == 10e6
        assert t.alternate_offset_hz == 20e6
        assert t.num_adjacent_channels == 2

    def test_nr_100mhz(self):
        t = ACLRTemplate.nr_100mhz()
        assert t.adjacent_offset_hz == 100e6

    def test_wlan_80mhz(self):
        t = ACLRTemplate.wlan_80mhz()
        assert t.adjacent_bandwidth_hz == 80e6

    def test_to_dict_roundtrip(self):
        t = ACLRTemplate.lte_10mhz()
        d = t.to_dict()
        t2 = ACLRTemplate.from_dict(d)
        assert t2.adjacent_offset_hz == t.adjacent_offset_hz


class TestEMIPrecomplianceTemplate:
    """Test EMIPrecomplianceTemplate presets."""

    def test_cispr_32_class_b(self):
        t = EMIPrecomplianceTemplate.cispr_32_class_b()
        assert t.config.rbw_hz == 9e3  # CISPR Band B
        assert t.config.detector_type == "QPE"
        assert t.config.trace_mode == "MAXHold"
        assert t.standard == "CISPR 32"
        assert t.emission_class == "B"
        assert "QPE" in t.detector_types
        assert "AVER" in t.detector_types

    def test_cispr_32_class_b_radiated(self):
        t = EMIPrecomplianceTemplate.cispr_32_class_b_radiated()
        assert t.config.rbw_hz == 120e3  # CISPR Band C/D
        assert t.config.detector_type == "QPE"

    def test_to_dict_roundtrip(self):
        t = EMIPrecomplianceTemplate.cispr_32_class_b()
        d = t.to_dict()
        t2 = EMIPrecomplianceTemplate.from_dict(d)
        assert t2.standard == t.standard
        assert t2.detector_types == t.detector_types


class TestSpuriousEmissionTemplate:
    """Test SpuriousEmissionTemplate presets."""

    def test_wideband(self):
        t = SpuriousEmissionTemplate.wideband_spurious()
        assert t.config.detector_type == "POS"
        assert t.config.trace_mode == "MAXHold"

    def test_harmonic_spurious(self):
        t = SpuriousEmissionTemplate.harmonic_spurious(1e9, 5)
        assert len(t.scan_ranges) == 5

    def test_to_dict_roundtrip(self):
        t = SpuriousEmissionTemplate.wideband_spurious()
        d = t.to_dict()
        t2 = SpuriousEmissionTemplate.from_dict(d)
        assert len(t2.scan_ranges) == len(t.scan_ranges)


class TestOccupiedBandwidthTemplate:
    """Test OccupiedBandwidthTemplate presets."""

    def test_lte_10mhz(self):
        t = OccupiedBandwidthTemplate.lte_10mhz()
        assert t.power_percentage == 99.0
        assert t.config.rbw_hz == 30e3

    def test_generic(self):
        t = OccupiedBandwidthTemplate.generic(2.4e9, 20e6)
        assert t.config.center_frequency_hz == 2.4e9


class TestHarmonicTemplate:
    """Test HarmonicTemplate."""

    def test_create(self):
        t = HarmonicTemplate.create(1e9, num_harmonics=5)
        assert t.fundamental_frequency_hz == 1e9
        assert t.num_harmonics == 5
        assert "harmonic_frequencies" in t.metadata

    def test_to_dict_roundtrip(self):
        t = HarmonicTemplate.create(100e6, num_harmonics=3)
        d = t.to_dict()
        t2 = HarmonicTemplate.from_dict(d)
        assert t2.fundamental_frequency_hz == 100e6
        assert t2.num_harmonics == 3
