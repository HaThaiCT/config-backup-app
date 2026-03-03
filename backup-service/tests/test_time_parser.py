"""Tests for time_parser module."""

import pytest

from src.utils.time_parser import (
    parse_duration,
    format_duration,
    seconds_to_duration_str,
)


class TestParseDuration:
    """Tests for parse_duration function."""
    
    def test_parse_one_day(self):
        """Test parsing 1 day."""
        assert parse_duration("01:00:00:00") == 86400
    
    def test_parse_one_hour(self):
        """Test parsing 1 hour."""
        assert parse_duration("00:01:00:00") == 3600
    
    def test_parse_one_minute(self):
        """Test parsing 1 minute."""
        assert parse_duration("00:00:01:00") == 60
    
    def test_parse_one_second(self):
        """Test parsing 1 second."""
        assert parse_duration("00:00:00:01") == 1
    
    def test_parse_complex_duration(self):
        """Test parsing complex duration."""
        # 2 days, 3 hours, 30 minutes, 45 seconds
        expected = 2 * 86400 + 3 * 3600 + 30 * 60 + 45
        assert parse_duration("02:03:30:45") == expected
    
    def test_parse_30_days(self):
        """Test parsing 30 days."""
        assert parse_duration("30:00:00:00") == 30 * 86400
    
    def test_parse_with_whitespace(self):
        """Test parsing with whitespace."""
        assert parse_duration("  01:00:00:00  ") == 86400
    
    def test_invalid_format_missing_parts(self):
        """Test invalid format with missing parts."""
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("01:00:00")
    
    def test_invalid_format_wrong_separator(self):
        """Test invalid format with wrong separator."""
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("01-00-00-00")
    
    def test_invalid_hours(self):
        """Test invalid hours (> 23)."""
        with pytest.raises(ValueError, match="Hours must be 0-23"):
            parse_duration("00:24:00:00")
    
    def test_invalid_minutes(self):
        """Test invalid minutes (> 59)."""
        with pytest.raises(ValueError, match="Minutes must be 0-59"):
            parse_duration("00:00:60:00")
    
    def test_invalid_seconds(self):
        """Test invalid seconds (> 59)."""
        with pytest.raises(ValueError, match="Seconds must be 0-59"):
            parse_duration("00:00:00:60")
    
    def test_zero_duration(self):
        """Test zero duration."""
        with pytest.raises(ValueError, match="Duration must be greater than 0"):
            parse_duration("00:00:00:00")


class TestFormatDuration:
    """Tests for format_duration function."""
    
    def test_format_seconds(self):
        """Test formatting seconds."""
        assert format_duration(45) == "45 seconds"
    
    def test_format_one_second(self):
        """Test formatting 1 second (singular)."""
        assert format_duration(1) == "1 second"
    
    def test_format_minutes(self):
        """Test formatting minutes."""
        assert format_duration(120) == "2 minutes"
    
    def test_format_one_minute(self):
        """Test formatting 1 minute."""
        assert format_duration(60) == "1 minute"
    
    def test_format_hours(self):
        """Test formatting hours."""
        assert format_duration(7200) == "2 hours"
    
    def test_format_days(self):
        """Test formatting days."""
        assert format_duration(172800) == "2 days"
    
    def test_format_complex(self):
        """Test formatting complex duration."""
        # 1 day, 2 hours, 30 minutes, 45 seconds
        seconds = 86400 + 7200 + 1800 + 45
        result = format_duration(seconds)
        assert "1 day" in result
        assert "2 hours" in result
        assert "30 minutes" in result
        assert "45 seconds" in result
    
    def test_format_zero(self):
        """Test formatting zero seconds."""
        assert format_duration(0) == "0 seconds"
    
    def test_negative_raises(self):
        """Test that negative seconds raises error."""
        with pytest.raises(ValueError):
            format_duration(-1)


class TestSecondsToDurationStr:
    """Tests for seconds_to_duration_str function."""
    
    def test_one_day(self):
        """Test converting 1 day."""
        assert seconds_to_duration_str(86400) == "01:00:00:00"
    
    def test_complex(self):
        """Test complex conversion."""
        seconds = 2 * 86400 + 3 * 3600 + 30 * 60 + 45
        assert seconds_to_duration_str(seconds) == "02:03:30:45"
    
    def test_zero(self):
        """Test zero seconds."""
        assert seconds_to_duration_str(0) == "00:00:00:00"
