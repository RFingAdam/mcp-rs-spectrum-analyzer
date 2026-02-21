"""Tests for safety validators."""

import pytest

from rs_spectrum_analyzer_mcp.exceptions import SafetyError
from rs_spectrum_analyzer_mcp.safety.validators import SafetyLimits, SafetyValidator


class TestSafetyLimits:
    """Test SafetyLimits defaults."""

    def test_defaults(self):
        limits = SafetyLimits()
        assert limits.max_input_power_dbm == 30.0
        assert limits.max_frequency_hz == 90e9
        assert limits.min_frequency_hz == 2.0
        assert limits.min_rbw_hz == 1.0
        assert limits.max_rbw_hz == 10e6
        assert limits.min_attenuation_db == 0.0
        assert limits.max_attenuation_db == 75.0

    def test_custom_limits(self):
        limits = SafetyLimits(
            max_frequency_hz=6e9,
            max_attenuation_db=50.0,
        )
        assert limits.max_frequency_hz == 6e9
        assert limits.max_attenuation_db == 50.0


class TestSafetyValidator:
    """Test SafetyValidator validation methods."""

    def setup_method(self):
        self.validator = SafetyValidator()

    def test_validate_frequency_valid(self):
        """Valid frequency should not raise."""
        self.validator.validate_frequency(1e9)
        self.validator.validate_frequency(2.0)  # Min
        self.validator.validate_frequency(90e9)  # Max

    def test_validate_frequency_too_high(self):
        with pytest.raises(SafetyError) as exc_info:
            self.validator.validate_frequency(100e9)
        assert exc_info.value.parameter == "frequency_hz"

    def test_validate_frequency_too_low(self):
        with pytest.raises(SafetyError) as exc_info:
            self.validator.validate_frequency(0.5)
        assert exc_info.value.parameter == "frequency_hz"

    def test_validate_frequency_range_valid(self):
        self.validator.validate_frequency_range(1e9, 2e9)

    def test_validate_frequency_range_invalid(self):
        with pytest.raises(ValueError):
            self.validator.validate_frequency_range(2e9, 1e9)

    def test_validate_reference_level_valid(self):
        self.validator.validate_reference_level(0.0)
        self.validator.validate_reference_level(-100.0)
        self.validator.validate_reference_level(30.0)

    def test_validate_reference_level_too_high(self):
        with pytest.raises(SafetyError):
            self.validator.validate_reference_level(50.0)

    def test_validate_reference_level_too_low(self):
        with pytest.raises(SafetyError):
            self.validator.validate_reference_level(-150.0)

    def test_validate_attenuation_valid(self):
        self.validator.validate_attenuation(0.0)
        self.validator.validate_attenuation(30.0)
        self.validator.validate_attenuation(75.0)

    def test_validate_attenuation_too_high(self):
        with pytest.raises(SafetyError):
            self.validator.validate_attenuation(80.0)

    def test_validate_attenuation_too_low(self):
        with pytest.raises(SafetyError):
            self.validator.validate_attenuation(-5.0)

    def test_validate_rbw_valid(self):
        self.validator.validate_rbw(1e3)
        self.validator.validate_rbw(1.0)
        self.validator.validate_rbw(10e6)

    def test_validate_rbw_too_high(self):
        with pytest.raises(SafetyError):
            self.validator.validate_rbw(20e6)

    def test_validate_rbw_too_low(self):
        with pytest.raises(SafetyError):
            self.validator.validate_rbw(0.1)

    def test_validate_input_power_valid(self):
        self.validator.validate_input_power(20.0)

    def test_validate_input_power_too_high(self):
        with pytest.raises(SafetyError):
            self.validator.validate_input_power(35.0)

    def test_custom_limits(self):
        """Validator with custom limits."""
        limits = SafetyLimits(max_frequency_hz=6e9)
        validator = SafetyValidator(limits)
        validator.validate_frequency(5e9)  # OK
        with pytest.raises(SafetyError):
            validator.validate_frequency(7e9)  # Too high
