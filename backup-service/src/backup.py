"""Backup functionality - create tar.gz archives."""

import logging
import os
import tarfile
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from .config import Config

logger = logging.getLogger(__name__)


def generate_backup_filename(config_name: str = "backup") -> str:
    """
    Generate backup filename with config name and timestamp.
    
    Args:
        config_name: Name of the config (used as prefix)
    
    Returns:
        Filename in format: {config_name}_YYYYMMDD_HHMMSS.tar.gz
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize config name (remove special characters)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in config_name)
    return f"{safe_name}_{timestamp}.tar.gz"


def validate_source_files(source_files: List[str]) -> Tuple[List[Path], List[str]]:
    """
    Validate source files exist.
    
    Args:
        source_files: List of file/directory paths
    
    Returns:
        Tuple of (valid_paths, missing_paths)
    """
    valid_paths = []
    missing_paths = []
    
    for file_path in source_files:
        path = Path(file_path)
        if path.exists():
            valid_paths.append(path)
        else:
            missing_paths.append(file_path)
    
    return valid_paths, missing_paths


def create_backup(config: Config) -> Path:
    """
    Create a backup archive of configured source files.
    
    Args:
        config: Configuration object
    
    Returns:
        Path to created backup file
    
    Raises:
        FileNotFoundError: If no source files exist
        OSError: If backup creation fails
    """
    source_files = config.backup.source_files
    destination = Path(config.backup.destination)
    
    # Ensure destination directory exists
    destination.mkdir(parents=True, exist_ok=True)
    
    # Validate source files
    valid_paths, missing_paths = validate_source_files(source_files)
    
    if missing_paths:
        for path in missing_paths:
            logger.warning(f"Source file not found, skipping: {path}")
    
    if not valid_paths:
        raise FileNotFoundError(
            f"No source files found. All paths are missing:\n"
            + "\n".join(f"  - {p}" for p in missing_paths)
        )
    
    # Generate backup filename with config name
    backup_filename = generate_backup_filename(config.name)
    backup_path = destination / backup_filename
    
    logger.info(f"[{config.name}] Creating backup: {backup_path}")
    
    # Create tar.gz archive
    try:
        with tarfile.open(backup_path, "w:gz") as tar:
            for path in valid_paths:
                # Use arcname to preserve directory structure from root
                arcname = str(path).lstrip("/").lstrip("\\")
                logger.debug(f"Adding: {path} -> {arcname}")
                tar.add(path, arcname=arcname)
                logger.info(f"Added: {path}")
        
        # Get file size
        file_size = backup_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        logger.info(
            f"Backup created successfully: {backup_path} ({file_size_mb:.2f} MB)"
        )
        
        return backup_path
    
    except Exception as e:
        # Clean up partial backup if it exists
        if backup_path.exists():
            backup_path.unlink()
        raise OSError(f"Failed to create backup: {e}") from e


def run_backup(config: Config) -> bool:
    """
    Run backup task.
    
    Args:
        config: Configuration object
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Starting backup...")
        backup_path = create_backup(config)
        logger.info(f"Backup completed: {backup_path}")
        return True
    except FileNotFoundError as e:
        logger.error(f"Backup failed - no source files: {e}")
        return False
    except OSError as e:
        logger.error(f"Backup failed - OS error: {e}")
        return False
    except Exception as e:
        logger.error(f"Backup failed - unexpected error: {e}")
        return False
