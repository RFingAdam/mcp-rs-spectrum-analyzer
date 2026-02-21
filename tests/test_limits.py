"""Tests for limit line system."""

import tempfile
from pathlib import Path

import pytest

from rs_spectrum_analyzer_mcp.limits import (
    LimitFailure,
    LimitLine,
    LimitManager,
    LimitResult,
    LimitSegment,
)
from rs_spectrum_analyzer_mcp.models.sa_types import TraceData


class TestLimitSegment:
    """Test LimitSegment."""

    def test_creation_with_max(self):
        seg = LimitSegment(
            start_freq_hz=1e9,
            stop_freq_hz=2e9,
            max_db=-30.0,
        )
        assert seg.max_db == -30.0
        assert seg.min_db is None

    def test_creation_with_both(self):
        seg = LimitSegment(
            start_freq_hz=1e9,
            stop_freq_hz=2e9,
            max_db=-30.0,
            min_db=-80.0,
        )
        assert seg.max_db == -30.0
        assert seg.min_db == -80.0

    def test_creation_without_limits_raises(self):
        with pytest.raises(ValueError, match="at least max_db or min_db"):
            LimitSegment(start_freq_hz=1e9, stop_freq_hz=2e9)

    def test_creation_invalid_range_raises(self):
        with pytest.raises(ValueError, match="less than"):
            LimitSegment(start_freq_hz=2e9, stop_freq_hz=1e9, max_db=-30.0)

    def test_contains_frequency(self):
        seg = LimitSegment(start_freq_hz=1e9, stop_freq_hz=2e9, max_db=-30.0)
        assert seg.contains_frequency(1.5e9) is True
        assert seg.contains_frequency(1e9) is True  # Start edge
        assert seg.contains_frequency(2e9) is True  # Stop edge
        assert seg.contains_frequency(0.5e9) is False
        assert seg.contains_frequency(3e9) is False

    def test_check_value_pass(self):
        seg = LimitSegment(start_freq_hz=1e9, stop_freq_hz=2e9, max_db=-30.0)
        assert seg.check_value(1.5e9, -40.0) is None  # Below limit = pass

    def test_check_value_fail_max(self):
        seg = LimitSegment(start_freq_hz=1e9, stop_freq_hz=2e9, max_db=-30.0)
        failure = seg.check_value(1.5e9, -20.0)
        assert failure is not None
        assert failure.limit_type == "max"

    def test_check_value_fail_min(self):
        seg = LimitSegment(start_freq_hz=1e9, stop_freq_hz=2e9, min_db=-80.0)
        failure = seg.check_value(1.5e9, -90.0)
        assert failure is not None
        assert failure.limit_type == "min"

    def test_check_value_outside_range(self):
        seg = LimitSegment(start_freq_hz=1e9, stop_freq_hz=2e9, max_db=-30.0)
        assert seg.check_value(500e6, -10.0) is None  # Outside range

    def test_to_dict_roundtrip(self):
        seg = LimitSegment(
            start_freq_hz=1e9,
            stop_freq_hz=2e9,
            max_db=-30.0,
            min_db=-80.0,
            name="test",
        )
        d = seg.to_dict()
        seg2 = LimitSegment.from_dict(d)
        assert seg2.start_freq_hz == seg.start_freq_hz
        assert seg2.max_db == seg.max_db
        assert seg2.name == seg.name


class TestLimitLine:
    """Test LimitLine."""

    def _make_trace(self) -> TraceData:
        """Create test trace data."""
        freqs = [1e9, 1.5e9, 2e9, 2.5e9, 3e9]
        amps = [-50.0, -40.0, -20.0, -45.0, -55.0]
        return TraceData(frequencies=freqs, amplitudes=amps)

    def test_check_all_pass(self):
        limit = LimitLine.create_flat_limit(
            "test", 1e9, 3e9, max_db=-10.0
        )
        trace = self._make_trace()
        result = limit.check(trace)
        assert result.passed is True
        assert result.failed_points == 0

    def test_check_with_failures(self):
        limit = LimitLine.create_flat_limit(
            "test", 1e9, 3e9, max_db=-30.0
        )
        trace = self._make_trace()
        result = limit.check(trace)
        assert result.passed is False
        assert result.failed_points > 0
        assert result.worst_failure is not None

    def test_check_single_point(self):
        limit = LimitLine.create_flat_limit(
            "test", 1e9, 3e9, max_db=-30.0
        )
        # Below limit
        assert limit.check_single_point(1.5e9, -40.0) is None
        # Above limit
        failure = limit.check_single_point(1.5e9, -20.0)
        assert failure is not None

    def test_get_limit_at_frequency(self):
        limit = LimitLine.create_flat_limit(
            "test", 1e9, 3e9, max_db=-30.0
        )
        result = limit.get_limit_at_frequency(2e9)
        assert result["max_db"] == -30.0

        result = limit.get_limit_at_frequency(500e6)
        assert result["max_db"] is None

    def test_save_load_roundtrip(self):
        limit = LimitLine.create_flat_limit(
            "test_limit", 1e9, 3e9, max_db=-30.0, min_db=-80.0
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            limit.save(filepath)
            loaded = LimitLine.load(filepath)
            assert loaded.name == "test_limit"
            assert len(loaded.segments) == 1
            assert loaded.segments[0].max_db == -30.0
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_create_emission_limit(self):
        segments = [
            {"start_freq_hz": 150e3, "stop_freq_hz": 500e3, "max_db": -34.0, "name": "Band A"},
            {"start_freq_hz": 500e3, "stop_freq_hz": 30e6, "max_db": -44.0, "name": "Band B"},
        ]
        limit = LimitLine.create_emission_limit("CISPR Test", segments)
        assert limit.name == "CISPR Test"
        assert len(limit.segments) == 2

    def test_to_dict_roundtrip(self):
        limit = LimitLine(
            name="test",
            segments=[
                LimitSegment(1e9, 2e9, max_db=-30.0, name="seg1"),
                LimitSegment(2e9, 3e9, max_db=-40.0, name="seg2"),
            ],
            description="Test limit",
        )
        d = limit.to_dict()
        loaded = LimitLine.from_dict(d)
        assert loaded.name == limit.name
        assert len(loaded.segments) == 2


class TestLimitManager:
    """Test LimitManager."""

    def test_add_and_list(self):
        mgr = LimitManager()
        limit = LimitLine.create_flat_limit("limit1", 1e9, 2e9, max_db=-30.0)
        mgr.add_limit(limit)
        assert "limit1" in mgr.list_limits()

    def test_remove(self):
        mgr = LimitManager()
        limit = LimitLine.create_flat_limit("limit1", 1e9, 2e9, max_db=-30.0)
        mgr.add_limit(limit)
        assert mgr.remove_limit("limit1") is True
        assert mgr.remove_limit("nonexistent") is False

    def test_clear(self):
        mgr = LimitManager()
        mgr.add_limit(LimitLine.create_flat_limit("l1", 1e9, 2e9, max_db=-30.0))
        mgr.add_limit(LimitLine.create_flat_limit("l2", 2e9, 3e9, max_db=-40.0))
        mgr.clear_limits()
        assert len(mgr.list_limits()) == 0

    def test_check_all(self):
        mgr = LimitManager()
        mgr.add_limit(LimitLine.create_flat_limit("l1", 1e9, 2e9, max_db=-30.0))

        trace = TraceData(
            frequencies=[1e9, 1.5e9, 2e9],
            amplitudes=[-50.0, -40.0, -35.0],
        )
        results = mgr.check_all(trace)
        assert "l1" in results
        assert results["l1"].passed is True

    def test_get_overall_status(self):
        mgr = LimitManager()
        mgr.add_limit(LimitLine.create_flat_limit("pass", 1e9, 2e9, max_db=-10.0))
        mgr.add_limit(LimitLine.create_flat_limit("fail", 1e9, 2e9, max_db=-60.0))

        trace = TraceData(
            frequencies=[1e9, 1.5e9, 2e9],
            amplitudes=[-50.0, -40.0, -35.0],
        )
        status = mgr.get_overall_status(trace)
        assert status["overall_passed"] is False
        assert status["limits_passed"] == 1
        assert status["limits_failed"] == 1


class TestLimitFailure:
    """Test LimitFailure."""

    def test_to_dict(self):
        failure = LimitFailure(
            frequency_hz=1.5e9,
            measured_value=-20.0,
            limit_value=-30.0,
            limit_type="max",
            segment_name="test_seg",
        )
        d = failure.to_dict()
        assert d["violation_db"] == 10.0
        assert d["segment_name"] == "test_seg"


class TestLimitResult:
    """Test LimitResult."""

    def test_pass_result(self):
        result = LimitResult(
            passed=True,
            failures=[],
            total_points=100,
            failed_points=0,
        )
        d = result.to_dict()
        assert d["passed"] is True
        assert d["pass_rate"] == 1.0

    def test_fail_result(self):
        failure = LimitFailure(1.5e9, -20.0, -30.0, "max")
        result = LimitResult(
            passed=False,
            failures=[failure],
            total_points=100,
            failed_points=1,
            worst_failure=failure,
        )
        d = result.to_dict()
        assert d["passed"] is False
        assert d["failure_count"] == 1
