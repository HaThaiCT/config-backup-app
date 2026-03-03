"""Configuration loader and validation."""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from .utils.time_parser import parse_duration

logger = logging.getLogger(__name__)


# Default config locations (in order of priority)
CONFIG_LOCATIONS = [
    Path(os.environ.get("BACKUP_CONFIG", "")),
    Path("/etc/backup-service/config.yaml"),
    Path("./config/config.yaml"),
    Path("./config.yaml"),
]

# Default conf.d directory locations
CONFD_LOCATIONS = [
    Path(os.environ.get("BACKUP_CONFD", "")),
    Path("/etc/backup-service/conf.d"),
    Path("./config/conf.d"),
    Path("./conf.d"),
]


class BackupConfig(BaseModel):
    """Backup configuration."""
    
    source_files: List[str] = Field(
        ...,
        min_length=1,
        description="List of files/directories to backup",
    )
    destination: str = Field(
        default="/backups",
        description="Backup destination directory",
    )
    
    @field_validator("source_files")
    @classmethod
    def validate_source_files(cls, v: List[str]) -> List[str]:
        """Validate source files list."""
        if not v:
            raise ValueError("source_files cannot be empty")
        return v
    
    @field_validator("destination")
    @classmethod
    def validate_destination(cls, v: str) -> str:
        """Validate destination path."""
        if not v:
            raise ValueError("destination cannot be empty")
        return v


class ScheduleConfig(BaseModel):
    """Schedule configuration."""
    
    backup_interval: str = Field(
        default="01:00:00:00",
        description="Backup interval in DD:HH:MM:SS format",
    )
    cleanup_interval: str = Field(
        default="01:00:00:00",
        description="Cleanup interval in DD:HH:MM:SS format",
    )
    
    # Parsed values (computed)
    backup_interval_seconds: int = Field(default=0, exclude=True)
    cleanup_interval_seconds: int = Field(default=0, exclude=True)
    
    @model_validator(mode="after")
    def parse_intervals(self) -> "ScheduleConfig":
        """Parse interval strings to seconds."""
        self.backup_interval_seconds = parse_duration(self.backup_interval)
        self.cleanup_interval_seconds = parse_duration(self.cleanup_interval)
        return self


class CleanupConfig(BaseModel):
    """Cleanup configuration."""
    
    ttl: str = Field(
        default="30:00:00:00",
        description="Time-to-live for backups in DD:HH:MM:SS format",
    )
    min_keep: int = Field(
        default=5,
        ge=1,
        description="Minimum number of backups to keep",
    )
    
    # Parsed value (computed)
    ttl_seconds: int = Field(default=0, exclude=True)
    
    @model_validator(mode="after")
    def parse_ttl(self) -> "CleanupConfig":
        """Parse TTL string to seconds."""
        self.ttl_seconds = parse_duration(self.ttl)
        return self


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )
    file: Optional[str] = Field(
        default=None,
        description="Log file path (None for console only)",
    )
    max_size_mb: int = Field(
        default=10,
        ge=1,
        description="Max log file size in MB",
    )
    backup_count: int = Field(
        default=5,
        ge=0,
        description="Number of backup log files to keep",
    )


class Config(BaseModel):
    """Root configuration model."""
    
    # Name to identify this config (derived from filename)
    name: str = Field(
        default="default",
        description="Config name (used in backup filenames)",
    )
    
    backup: BackupConfig
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    cleanup: CleanupConfig = Field(default_factory=CleanupConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def find_config_file() -> Path:
    """
    Find configuration file from known locations.
    
    Returns:
        Path to config file
    
    Raises:
        FileNotFoundError: If no config file found
    """
    for path in CONFIG_LOCATIONS:
        if path and path.exists() and path.is_file():
            logger.debug(f"Found config file: {path}")
            return path
    
    searched = [str(p) for p in CONFIG_LOCATIONS if p]
    raise FileNotFoundError(
        f"Config file not found. Searched locations:\n"
        + "\n".join(f"  - {p}" for p in searched)
    )


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load and validate configuration from YAML file.
    
    Args:
        config_path: Optional explicit path to config file
    
    Returns:
        Validated Config object
    
    Raises:
        FileNotFoundError: If config file not found
        ValueError: If config validation fails
    """
    if config_path is None:
        config_path = find_config_file()
    
    logger.info(f"Loading config from: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)
    
    if raw_config is None:
        raise ValueError(f"Config file is empty: {config_path}")
    
    try:
        config = Config(**raw_config)
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}") from e
    
    # Set name from filename if not specified
    if config.name == "default" and config_path:
        config.name = config_path.stem  # filename without extension
    
    logger.debug(f"Config '{config.name}' loaded successfully")
    return config


def find_confd_directory() -> Optional[Path]:
    """
    Find conf.d directory from known locations.
    
    Returns:
        Path to conf.d directory or None if not found
    """
    for path in CONFD_LOCATIONS:
        # Skip empty paths (from env vars that aren't set)
        if not path or str(path) in ("", "."):
            continue
        if path.exists() and path.is_dir():
            # Verify directory has yaml files
            yaml_files = list(path.glob("*.yaml")) + list(path.glob("*.yml"))
            if yaml_files:
                logger.debug(f"Found conf.d directory: {path} with {len(yaml_files)} config(s)")
                return path
    return None


def load_all_configs() -> List[Config]:
    """
    Load all configurations from conf.d directory.
    
    If conf.d exists and has .yaml files, load all of them.
    Otherwise, fall back to single config.yaml.
    
    Returns:
        List of Config objects
    
    Raises:
        FileNotFoundError: If no config found
        ValueError: If config validation fails
    """
    configs = []
    
    # Try to find conf.d directory
    confd_path = find_confd_directory()
    
    if confd_path:
        # Load all .yaml files from conf.d
        yaml_files = sorted(confd_path.glob("*.yaml")) + sorted(confd_path.glob("*.yml"))
        
        if yaml_files:
            logger.info(f"Loading configs from: {confd_path}")
            
            for yaml_file in yaml_files:
                try:
                    config = load_config(yaml_file)
                    configs.append(config)
                    logger.info(f"  Loaded: {yaml_file.name} (name: {config.name})")
                except Exception as e:
                    logger.error(f"  Failed to load {yaml_file.name}: {e}")
            
            if configs:
                logger.info(f"Loaded {len(configs)} config(s) from conf.d")
                return configs
    
    # Fallback to single config.yaml
    logger.debug("No conf.d configs found, falling back to single config")
    config = load_config()
    return [config]


def get_merged_logging_config(configs: List[Config]) -> LoggingConfig:
    """
    Get logging config (use first config's logging settings).
    
    Args:
        configs: List of configs
    
    Returns:
        LoggingConfig from first config
    """
    if configs:
        return configs[0].logging
    return LoggingConfig()
