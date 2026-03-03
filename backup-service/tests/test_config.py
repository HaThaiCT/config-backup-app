"""Tests for config module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.config import Config, load_config, BackupConfig, ScheduleConfig, CleanupConfig


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_config_data():
    """Return valid configuration data."""
    return {
        "backup": {
            "source_files": ["/etc/nginx/nginx.conf", "/etc/ssh/sshd_config"],
            "destination": "/backups",
        },
        "schedule": {
            "backup_interval": "01:00:00:00",
            "cleanup_interval": "00:12:00:00",
        },
        "cleanup": {
            "ttl": "30:00:00:00",
            "min_keep": 5,
        },
        "logging": {
            "level": "INFO",
            "file": "/var/log/backup.log",
        },
    }


@pytest.fixture
def config_file(temp_dir, valid_config_data):
    """Create a valid config file."""
    config_path = temp_dir / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(valid_config_data, f)
    return config_path


class TestBackupConfig:
    """Tests for BackupConfig model."""
    
    def test_valid_config(self):
        """Test valid backup config."""
        config = BackupConfig(
            source_files=["/etc/nginx.conf"],
            destination="/backups",
        )
        assert len(config.source_files) == 1
        assert config.destination == "/backups"
    
    def test_empty_source_files_raises(self):
        """Test that empty source_files raises error."""
        with pytest.raises(ValueError):
            BackupConfig(source_files=[], destination="/backups")
    
    def test_default_destination(self):
        """Test default destination."""
        config = BackupConfig(source_files=["/etc/nginx.conf"])
        assert config.destination == "/backups"


class TestScheduleConfig:
    """Tests for ScheduleConfig model."""
    
    def test_valid_config(self):
        """Test valid schedule config."""
        config = ScheduleConfig(
            backup_interval="01:00:00:00",
            cleanup_interval="00:06:00:00",
        )
        assert config.backup_interval_seconds == 86400
        assert config.cleanup_interval_seconds == 6 * 3600
    
    def test_default_values(self):
        """Test default values."""
        config = ScheduleConfig()
        assert config.backup_interval == "01:00:00:00"
        assert config.cleanup_interval == "01:00:00:00"
    
    def test_invalid_interval_format(self):
        """Test invalid interval format raises error."""
        with pytest.raises(ValueError):
            ScheduleConfig(backup_interval="invalid")


class TestCleanupConfig:
    """Tests for CleanupConfig model."""
    
    def test_valid_config(self):
        """Test valid cleanup config."""
        config = CleanupConfig(
            ttl="30:00:00:00",
            min_keep=5,
        )
        assert config.ttl_seconds == 30 * 86400
        assert config.min_keep == 5
    
    def test_min_keep_minimum(self):
        """Test that min_keep must be at least 1."""
        with pytest.raises(ValueError):
            CleanupConfig(ttl="01:00:00:00", min_keep=0)


class TestConfig:
    """Tests for Config model."""
    
    def test_valid_config(self, valid_config_data):
        """Test valid full config."""
        config = Config(**valid_config_data)
        assert len(config.backup.source_files) == 2
        assert config.schedule.backup_interval_seconds == 86400
        assert config.cleanup.ttl_seconds == 30 * 86400
    
    def test_minimal_config(self):
        """Test minimal config (only required fields)."""
        config = Config(
            backup={"source_files": ["/etc/test.conf"]},
        )
        assert config.backup.destination == "/backups"
        assert config.schedule.backup_interval == "01:00:00:00"
        assert config.cleanup.min_keep == 5


class TestLoadConfig:
    """Tests for load_config function."""
    
    def test_load_valid_config(self, config_file):
        """Test loading valid config file."""
        config = load_config(config_file)
        assert isinstance(config, Config)
    
    def test_file_not_found(self, temp_dir):
        """Test loading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_config(temp_dir / "nonexistent.yaml")
    
    def test_invalid_yaml(self, temp_dir):
        """Test loading invalid YAML raises error."""
        invalid_file = temp_dir / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: [[[")
        
        with pytest.raises(Exception):
            load_config(invalid_file)
    
    def test_empty_config_raises(self, temp_dir):
        """Test that empty config file raises error."""
        empty_file = temp_dir / "empty.yaml"
        empty_file.write_text("")
        
        with pytest.raises(ValueError, match="empty"):
            load_config(empty_file)
