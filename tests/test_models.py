"""Tests for data models."""

from spectrum_analyzer_mcp.models.sa_types import (
    ACLRResult,
    BandwidthResult,
    ChannelPowerResult,
    DetectorType,
    InstrumentInfo,
    InstrumentVendor,
    MarkerData,
    OBWResult,
    SEMResult,
    SpectrumAnalyzerFamily,
    TraceData,
    TraceMode,
)


class TestSpectrumAnalyzerFamily:
    """Test SpectrumAnalyzerFamily enum."""

    def test_fsw_max_frequency(self):
        assert SpectrumAnalyzerFamily.FSW.max_frequency_hz == 90e9

    def test_fpl1000_max_frequency(self):
        assert SpectrumAnalyzerFamily.FPL1000.max_frequency_hz == 40e9

    def test_all_families_have_preamp(self):
        for family in SpectrumAnalyzerFamily:
            assert family.has_preamp is True


class TestTraceMode:
    """Test TraceMode enum values."""

    def test_write_mode(self):
        assert TraceMode.WRITE.value == "WRITe"

    def test_max_hold_mode(self):
        assert TraceMode.MAX_HOLD.value == "MAXHold"

    def test_min_hold_mode(self):
        assert TraceMode.MIN_HOLD.value == "MINHold"

    def test_average_mode(self):
        assert TraceMode.AVERAGE.value == "AVERage"


class TestDetectorType:
    """Test DetectorType enum values."""

    def test_peak(self):
        assert DetectorType.PEAK.value == "POS"

    def test_rms(self):
        assert DetectorType.RMS.value == "RMS"

    def test_quasi_peak(self):
        assert DetectorType.QUASI_PEAK.value == "QPE"

    def test_sample(self):
        assert DetectorType.SAMPLE.value == "SAMP"

    def test_cispr_average(self):
        assert DetectorType.CISPR_AVERAGE.value == "CAV"


class TestInstrumentInfo:
    """Test InstrumentInfo model."""

    def test_from_idn(self):
        idn = "Rohde&Schwarz,FSW-26,1312.8000K26/100001,4.30.018.28"
        info = InstrumentInfo.from_idn(idn)
        assert info.manufacturer == "Rohde&Schwarz"
        assert info.model == "FSW-26"
        assert info.serial_number == "1312.8000K26/100001"
        assert info.firmware_version == "4.30.018.28"

    def test_detect_family_fsw(self):
        info = InstrumentInfo("Rohde&Schwarz", "FSW-26", "12345", "1.0")
        assert info.detect_family() == SpectrumAnalyzerFamily.FSW

    def test_detect_family_fsva(self):
        info = InstrumentInfo("Rohde&Schwarz", "FSVA3007", "12345", "1.0")
        assert info.detect_family() == SpectrumAnalyzerFamily.FSVA3000

    def test_detect_family_fsv(self):
        info = InstrumentInfo("Rohde&Schwarz", "FSV3030", "12345", "1.0")
        assert info.detect_family() == SpectrumAnalyzerFamily.FSV3000

    def test_detect_family_fpl(self):
        info = InstrumentInfo("Rohde&Schwarz", "FPL1007", "12345", "1.0")
        assert info.detect_family() == SpectrumAnalyzerFamily.FPL1000

    def test_detect_family_unknown(self):
        info = InstrumentInfo("Unknown", "SomeModel", "12345", "1.0")
        assert info.detect_family() is None

    def test_to_dict(self):
        info = InstrumentInfo("Rohde&Schwarz", "FSW-26", "12345", "1.0")
        d = info.to_dict()
        assert d["manufacturer"] == "Rohde&Schwarz"
        assert d["model"] == "FSW-26"
        assert d["vendor"] == "Rohde & Schwarz"

    def test_detect_vendor_rohde_schwarz(self):
        info = InstrumentInfo("Rohde&Schwarz", "FSW-26", "12345", "1.0")
        assert info.detect_vendor() == InstrumentVendor.ROHDE_SCHWARZ

    def test_detect_vendor_keysight(self):
        info = InstrumentInfo("Keysight Technologies", "N9040B", "12345", "1.0")
        assert info.detect_vendor() == InstrumentVendor.KEYSIGHT

    def test_detect_vendor_rigol(self):
        info = InstrumentInfo("RIGOL TECHNOLOGIES", "DSA832E", "12345", "1.0")
        assert info.detect_vendor() == InstrumentVendor.RIGOL

    def test_detect_vendor_siglent(self):
        info = InstrumentInfo("Siglent Technologies", "SSA3021X", "12345", "1.0")
        assert info.detect_vendor() == InstrumentVendor.SIGLENT

    def test_detect_vendor_unknown(self):
        info = InstrumentInfo("SomeMfr", "SomeModel", "12345", "1.0")
        assert info.detect_vendor() == InstrumentVendor.UNKNOWN


class TestTraceData:
    """Test TraceData model."""

    def test_basic_trace(self):
        trace = TraceData(
            frequencies=[1e9, 1.5e9, 2e9],
            amplitudes=[-80.0, -60.0, -75.0],
        )
        assert trace.num_points == 3
        assert trace.peak_amplitude == -60.0
        assert trace.peak_frequency == 1.5e9

    def test_empty_trace(self):
        trace = TraceData(frequencies=[], amplitudes=[])
        assert trace.num_points == 0
        assert trace.peak_amplitude == float("-inf")
        assert trace.peak_frequency == 0.0

    def test_to_dict(self):
        trace = TraceData(
            frequencies=[1e9, 2e9],
            amplitudes=[-80.0, -70.0],
            trace_number=1,
            rbw_hz=1e3,
        )
        d = trace.to_dict()
        assert d["num_points"] == 2
        assert d["rbw_hz"] == 1e3
        assert d["peak_amplitude_dbm"] == -70.0

    def test_to_summary(self):
        trace = TraceData(
            frequencies=[1e9, 2e9],
            amplitudes=[-80.0, -70.0],
        )
        s = trace.to_summary()
        assert s["start_freq_hz"] == 1e9
        assert s["stop_freq_hz"] == 2e9
        assert "frequencies" not in s  # Summary excludes raw data


class TestMarkerData:
    """Test MarkerData model."""

    def test_basic_marker(self):
        marker = MarkerData(
            marker_number=1,
            frequency_hz=1e9,
            amplitude_dbm=-60.5,
        )
        d = marker.to_dict()
        assert d["marker_number"] == 1
        assert d["frequency_hz"] == 1e9
        assert d["amplitude_dbm"] == -60.5
        assert d["delta_mode"] is False

    def test_delta_marker(self):
        marker = MarkerData(
            marker_number=2,
            frequency_hz=1.5e9,
            amplitude_dbm=-55.0,
            delta_mode=True,
            delta_frequency_hz=500e6,
            delta_amplitude_db=5.5,
        )
        d = marker.to_dict()
        assert d["delta_mode"] is True
        assert d["delta_frequency_hz"] == 500e6


class TestChannelPowerResult:
    """Test ChannelPowerResult model."""

    def test_to_dict(self):
        result = ChannelPowerResult(
            channel_power_dbm=-20.5,
            channel_power_density_dbm_hz=-90.3,
            channel_bandwidth_hz=10e6,
            center_frequency_hz=1e9,
        )
        d = result.to_dict()
        assert d["channel_power_dbm"] == -20.5
        assert d["channel_bandwidth_hz"] == 10e6


class TestACLRResult:
    """Test ACLRResult model."""

    def test_basic_aclr(self):
        result = ACLRResult(
            channel_power_dbm=-20.0,
            lower_adjacent_dbm=-60.0,
            upper_adjacent_dbm=-58.0,
            lower_aclr_db=40.0,
            upper_aclr_db=38.0,
        )
        d = result.to_dict()
        assert d["lower_aclr_db"] == 40.0
        assert "lower_alternate_dbm" not in d

    def test_aclr_with_alternate(self):
        result = ACLRResult(
            channel_power_dbm=-20.0,
            lower_adjacent_dbm=-60.0,
            upper_adjacent_dbm=-58.0,
            lower_aclr_db=40.0,
            upper_aclr_db=38.0,
            lower_alternate_dbm=-70.0,
            upper_alternate_dbm=-68.0,
            lower_alternate_aclr_db=50.0,
            upper_alternate_aclr_db=48.0,
        )
        d = result.to_dict()
        assert d["lower_alternate_dbm"] == -70.0


class TestSEMResult:
    """Test SEMResult model."""

    def test_passed(self):
        result = SEMResult(passed=True, tx_power_dbm=-10.0)
        d = result.to_dict()
        assert d["passed"] is True

    def test_failed(self):
        result = SEMResult(
            passed=False,
            tx_power_dbm=-10.0,
            violations=[{"limit": -36.0, "measured": -30.0}],
        )
        d = result.to_dict()
        assert d["passed"] is False
        assert len(d["violations"]) == 1


class TestOBWResult:
    """Test OBWResult model."""

    def test_to_dict(self):
        result = OBWResult(
            occupied_bandwidth_hz=9.5e6,
            center_frequency_hz=1e9,
            power_percentage=99.0,
        )
        d = result.to_dict()
        assert d["occupied_bandwidth_hz"] == 9.5e6
        assert d["power_percentage"] == 99.0


class TestBandwidthResult:
    """Test BandwidthResult model."""

    def test_basic_bandwidth(self):
        result = BandwidthResult(
            bandwidth_hz=1e6,
            center_frequency_hz=1e9,
        )
        assert result.bandwidth_hz == 1e6
        assert result.center_frequency_hz == 1e9
        assert result.n_db == 3.0
        assert result.lower_frequency_hz is None
        assert result.upper_frequency_hz is None
        assert result.quality_factor is None

    def test_full_bandwidth(self):
        result = BandwidthResult(
            bandwidth_hz=2e6,
            center_frequency_hz=1e9,
            n_db=6.0,
            lower_frequency_hz=999e6,
            upper_frequency_hz=1001e6,
            quality_factor=500.0,
        )
        assert result.n_db == 6.0
        assert result.lower_frequency_hz == 999e6
        assert result.upper_frequency_hz == 1001e6
        assert result.quality_factor == 500.0

    def test_to_dict_minimal(self):
        result = BandwidthResult(
            bandwidth_hz=1e6,
            center_frequency_hz=1e9,
        )
        d = result.to_dict()
        assert d["bandwidth_hz"] == 1e6
        assert d["center_frequency_hz"] == 1e9
        assert d["n_db"] == 3.0
        assert "lower_frequency_hz" not in d
        assert "upper_frequency_hz" not in d
        assert "quality_factor" not in d

    def test_to_dict_full(self):
        result = BandwidthResult(
            bandwidth_hz=2e6,
            center_frequency_hz=1e9,
            n_db=6.0,
            lower_frequency_hz=999e6,
            upper_frequency_hz=1001e6,
            quality_factor=500.0,
        )
        d = result.to_dict()
        assert d["bandwidth_hz"] == 2e6
        assert d["center_frequency_hz"] == 1e9
        assert d["n_db"] == 6.0
        assert d["lower_frequency_hz"] == 999e6
        assert d["upper_frequency_hz"] == 1001e6
        assert d["quality_factor"] == 500.0
