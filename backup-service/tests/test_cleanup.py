"""Tests for cleanup module."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.cleanup import (
    parse_backup_timestamp,
    get_backup_files,
    calculate_age_seconds,
    run_cleanup,
)
from src.config import Config


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def backup_dir_with_files(temp_dir):
    """Create backup directory with sample backup files."""
    backup_dir = temp_dir / "backups"
    backup_dir.mkdir()
    
    # Create backup files with different timestamps
    timestamps = [
        "20260101_120000",  # Old
        "20260201_120000",  # Medium
        "20260301_120000",  # Recent
        "20260302_120000",  # Very recent
        "20260303_120000",  # Today
    ]
    
    for ts in timestamps:
        file_path = backup_dir / f"backup_{ts}.tar.gz"
        file_path.write_bytes(b"fake backup content " * 100)
    
    return backup_dir


@pytest.fixture
def cleanup_config(backup_dir_with_files):
    """Create test configuration for cleanup."""
    return Config(
        backup={
            "source_files": ["/etc/test.conf"],
            "destination": str(backup_dir_with_files),
        },
        schedule={
            "backup_interval": "01:00:00:00",
            "cleanup_interval": "01:00:00:00",
        },
        cleanup={
            "ttl": "30:00:00:00",  # 30 days
            "min_keep": 2,
        },
        logging={
            "level": "DEBUG",
        },
    )


class TestParseBackupTimestamp:
    """Tests for parse_backup_timestamp function."""
    
    def test_valid_filename(self):
        """Test parsing valid backup filename."""
        result = parse_backup_timestamp("backup_20260303_103015.tar.gz")
        assert result is not None
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 3
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 15
    
    def test_invalid_filename(self):
        """Test parsing invalid filename."""
        assert parse_backup_timestamp("not_a_backup.tar.gz") is None
        assert parse_backup_timestamp("backup_invalid.tar.gz") is None
        assert parse_backup_timestamp("backup_20260303.tar.gz") is None
    
    def test_wrong_extension(self):
        """Test parsing filename with wrong extension."""
        assert parse_backup_timestamp("backup_20260303_103015.zip") is None


class TestGetBackupFiles:
    """Tests for get_backup_files function."""
    
    def test_get_files(self, backup_dir_with_files):
        """Test getting backup files."""
        files = get_backup_files(backup_dir_with_files)
        assert len(files) == 5
    
    def test_sorted_newest_first(self, backup_dir_with_files):
        """Test that files are sorted newest first."""
        files = get_backup_files(backup_dir_with_files)
        timestamps = [f[1] for f in files]
        assert timestamps == sorted(timestamps, reverse=True)
    
    def test_empty_directory(self, temp_dir):
        """Test with empty directory."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()
        files = get_backup_files(empty_dir)
        assert len(files) == 0
    
    def test_nonexistent_directory(self, temp_dir):
        """Test with nonexistent directory."""
        files = get_backup_files(temp_dir / "nonexistent")
        assert len(files) == 0
    
    def test_ignores_non_backup_files(self, backup_dir_with_files):
        """Test that non-backup files are ignored."""
        # Create a non-backup file
        (backup_dir_with_files / "random_file.txt").write_text("not a backup")
        
        files = get_backup_files(backup_dir_with_files)
        assert len(files) == 5  # Still only 5 backup files


class TestCalculateAgeSeconds:
    """Tests for calculate_age_seconds function."""
    
    def test_recent_timestamp(self):
        """Test calculating age of recent timestamp."""
        recent = datetime.now() - timedelta(seconds=60)
        age = calculate_age_seconds(recent)
        assert 60 <= age < 65  # Allow some tolerance
    
    def test_old_timestamp(self):
        """Test calculating age of old timestamp."""
        old = datetime.now() - timedelta(days=30)
        age = calculate_age_seconds(old)
        expected = 30 * 86400
        assert expected <= age < expected + 60


class TestRunCleanup:
    """Tests for run_cleanup function."""
    
    def test_cleanup_respects_min_keep(self, backup_dir_with_files):
        """Test that cleanup respects min_keep."""
        config = Config(
            backup={
                "source_files": ["/etc/test.conf"],
                "destination": str(backup_dir_with_files),
            },
            cleanup={
                "ttl": "00:00:00:01",  # 1 second (everything is old)
                "min_keep": 3,
            },
        )
        
        deleted, _ = run_cleanup(config)
        
        # Should keep 3 (min_keep), delete 2
        remaining = list(backup_dir_with_files.glob("backup_*.tar.gz"))
        assert len(remaining) >= 3
    
    def test_cleanup_empty_dir(self, temp_dir):
        """Test cleanup with empty directory."""
        empty_dir = temp_dir / "empty_backups"
        empty_dir.mkdir()
        
        config = Config(
            backup={
                "source_files": ["/etc/test.conf"],
                "destination": str(empty_dir),
            },
            cleanup={
                "ttl": "01:00:00:00",
                "min_keep": 5,
            },
        )
        
        deleted, freed = run_cleanup(config)
        assert deleted == 0
        assert freed == 0
