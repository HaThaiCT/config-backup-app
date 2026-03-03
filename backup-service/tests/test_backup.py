"""Tests for backup module."""

import os
import tarfile
import tempfile
from pathlib import Path

import pytest

from src.backup import (
    generate_backup_filename,
    validate_source_files,
    create_backup,
    run_backup,
)
from src.config import Config


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample files for backup testing."""
    files = []
    
    # Create some test files
    for i in range(3):
        file_path = temp_dir / f"test_file_{i}.conf"
        file_path.write_text(f"Test content {i}\n" * 100)
        files.append(str(file_path))
    
    # Create a subdirectory with files
    subdir = temp_dir / "subdir"
    subdir.mkdir()
    sub_file = subdir / "nested.conf"
    sub_file.write_text("Nested content\n")
    files.append(str(subdir))
    
    return files


@pytest.fixture
def backup_config(temp_dir, sample_files):
    """Create test configuration."""
    backup_dir = temp_dir / "backups"
    backup_dir.mkdir()
    
    return Config(
        backup={
            "source_files": sample_files,
            "destination": str(backup_dir),
        },
        schedule={
            "backup_interval": "01:00:00:00",
            "cleanup_interval": "01:00:00:00",
        },
        cleanup={
            "ttl": "30:00:00:00",
            "min_keep": 5,
        },
        logging={
            "level": "DEBUG",
        },
    )


class TestGenerateBackupFilename:
    """Tests for generate_backup_filename function."""
    
    def test_filename_format(self):
        """Test that filename has correct format."""
        filename = generate_backup_filename()
        assert filename.startswith("backup_")
        assert filename.endswith(".tar.gz")
    
    def test_filename_contains_timestamp(self):
        """Test that filename contains timestamp."""
        filename = generate_backup_filename()
        # Format: backup_YYYYMMDD_HHMMSS.tar.gz
        parts = filename.replace("backup_", "").replace(".tar.gz", "")
        date_part, time_part = parts.split("_")
        assert len(date_part) == 8  # YYYYMMDD
        assert len(time_part) == 6  # HHMMSS


class TestValidateSourceFiles:
    """Tests for validate_source_files function."""
    
    def test_all_valid(self, sample_files):
        """Test with all valid files."""
        valid, missing = validate_source_files(sample_files)
        assert len(valid) == len(sample_files)
        assert len(missing) == 0
    
    def test_some_missing(self, sample_files):
        """Test with some missing files."""
        files = sample_files + ["/nonexistent/file.conf"]
        valid, missing = validate_source_files(files)
        assert len(valid) == len(sample_files)
        assert len(missing) == 1
    
    def test_all_missing(self):
        """Test with all missing files."""
        files = ["/nonexistent/file1.conf", "/nonexistent/file2.conf"]
        valid, missing = validate_source_files(files)
        assert len(valid) == 0
        assert len(missing) == 2


class TestCreateBackup:
    """Tests for create_backup function."""
    
    def test_create_backup_success(self, backup_config, temp_dir):
        """Test successful backup creation."""
        backup_path = create_backup(backup_config)
        
        assert backup_path.exists()
        assert backup_path.suffix == ".gz"
        assert backup_path.stem.endswith(".tar")
    
    def test_backup_contains_files(self, backup_config, temp_dir):
        """Test that backup contains expected files."""
        backup_path = create_backup(backup_config)
        
        with tarfile.open(backup_path, "r:gz") as tar:
            names = tar.getnames()
            assert len(names) > 0
    
    def test_backup_destination_created(self, temp_dir, sample_files):
        """Test that destination directory is created if needed."""
        new_dest = temp_dir / "new_backup_dir"
        
        config = Config(
            backup={
                "source_files": sample_files,
                "destination": str(new_dest),
            },
        )
        
        backup_path = create_backup(config)
        assert new_dest.exists()
        assert backup_path.exists()
    
    def test_no_source_files_raises(self, temp_dir):
        """Test that missing source files raises error."""
        config = Config(
            backup={
                "source_files": ["/nonexistent/file.conf"],
                "destination": str(temp_dir / "backups"),
            },
        )
        
        with pytest.raises(FileNotFoundError):
            create_backup(config)


class TestRunBackup:
    """Tests for run_backup function."""
    
    def test_run_backup_success(self, backup_config):
        """Test successful backup run."""
        result = run_backup(backup_config)
        assert result is True
    
    def test_run_backup_failure(self, temp_dir):
        """Test backup run with no valid files."""
        config = Config(
            backup={
                "source_files": ["/nonexistent/file.conf"],
                "destination": str(temp_dir / "backups"),
            },
        )
        
        result = run_backup(config)
        assert result is False
