"""Tests for exception hierarchy."""

from spectrum_analyzer_mcp.exceptions import (
    CommunicationError,
    ConfigurationError,
    ConnectionError,
    MeasurementError,
    SafetyError,
    SpectrumAnalyzerError,
    TimeoutError,
)


class TestExceptionHierarchy:
    """Test that all exceptions inherit from SpectrumAnalyzerError."""

    def test_base_exception(self):
        err = SpectrumAnalyzerError("test error")
        assert str(err) == "test error"
        assert err.message == "test error"
        assert err.address is None

    def test_base_exception_with_address(self):
        err = SpectrumAnalyzerError("test error", address="192.168.1.100:5025")
        assert "192.168.1.100:5025" in str(err)

    def test_connection_error(self):
        err = ConnectionError("cannot connect")
        assert isinstance(err, SpectrumAnalyzerError)

    def test_communication_error(self):
        err = CommunicationError("timeout")
        assert isinstance(err, SpectrumAnalyzerError)

    def test_configuration_error(self):
        err = ConfigurationError("bad config")
        assert isinstance(err, SpectrumAnalyzerError)

    def test_measurement_error(self):
        err = MeasurementError("measurement failed")
        assert isinstance(err, SpectrumAnalyzerError)

    def test_timeout_error(self):
        err = TimeoutError("timed out")
        assert isinstance(err, SpectrumAnalyzerError)

    def test_safety_error(self):
        err = SafetyError(
            "frequency too high",
            parameter="frequency_hz",
            value=100e9,
            limit=90e9,
        )
        assert isinstance(err, SpectrumAnalyzerError)
        assert err.parameter == "frequency_hz"
        assert err.value == 100e9
        assert err.limit == 90e9
