"""Cleanup functionality - remove old backups based on TTL."""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from .config import Config

logger = logging.getLogger(__name__)

# Pattern to match backup files: backup_YYYYMMDD_HHMMSS.tar.gz
BACKUP_PATTERN = re.compile(r"^backup_(\d{8}_\d{6})\.tar\.gz$")


def parse_backup_timestamp(filename: str) -> datetime | None:
    """
    Parse timestamp from backup filename.
    
    Args:
        filename: Backup filename (e.g., backup_20260303_103015.tar.gz)
    
    Returns:
        datetime object or None if parsing fails
    """
    match = BACKUP_PATTERN.match(filename)
    if not match:
        return None
    
    try:
        timestamp_str = match.group(1)
        return datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
    except ValueError:
        return None


def get_backup_files(backup_dir: Path) -> List[Tuple[Path, datetime]]:
    """
    Get list of backup files with their timestamps.
    
    Args:
        backup_dir: Directory containing backups
    
    Returns:
        List of (path, timestamp) tuples, sorted by timestamp (newest first)
    """
    if not backup_dir.exists():
        return []
    
    backups = []
    
    for file_path in backup_dir.iterdir():
        if not file_path.is_file():
            continue
        
        timestamp = parse_backup_timestamp(file_path.name)
        if timestamp:
            backups.append((file_path, timestamp))
    
    # Sort by timestamp, newest first
    backups.sort(key=lambda x: x[1], reverse=True)
    
    return backups


def calculate_age_seconds(timestamp: datetime) -> int:
    """
    Calculate age of backup in seconds.
    
    Args:
        timestamp: Backup creation timestamp
    
    Returns:
        Age in seconds
    """
    now = datetime.now()
    delta = now - timestamp
    return int(delta.total_seconds())


def run_cleanup(config: Config) -> Tuple[int, int]:
    """
    Run cleanup task - remove backups older than TTL.
    
    Respects min_keep setting to always keep minimum number of backups.
    
    Args:
        config: Configuration object
    
    Returns:
        Tuple of (deleted_count, freed_bytes)
    """
    backup_dir = Path(config.backup.destination)
    ttl_seconds = config.cleanup.ttl_seconds
    min_keep = config.cleanup.min_keep
    
    logger.info(
        f"Starting cleanup: TTL={config.cleanup.ttl}, min_keep={min_keep}"
    )
    
    # Get all backup files
    backups = get_backup_files(backup_dir)
    total_count = len(backups)
    
    if total_count == 0:
        logger.info("No backup files found")
        return 0, 0
    
    logger.info(f"Found {total_count} backup files")
    
    deleted_count = 0
    freed_bytes = 0
    
    for i, (file_path, timestamp) in enumerate(backups):
        # Always keep min_keep newest backups
        if i < min_keep:
            logger.debug(f"Keeping (min_keep): {file_path.name}")
            continue
        
        # Check age against TTL
        age_seconds = calculate_age_seconds(timestamp)
        
        if age_seconds > ttl_seconds:
            try:
                file_size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                freed_bytes += file_size
                
                age_days = age_seconds / 86400
                logger.info(
                    f"Deleted: {file_path.name} ({age_days:.1f} days old)"
                )
            except OSError as e:
                logger.error(f"Failed to delete {file_path}: {e}")
        else:
            logger.debug(f"Keeping (within TTL): {file_path.name}")
    
    freed_mb = freed_bytes / (1024 * 1024)
    logger.info(
        f"Cleanup completed: deleted {deleted_count} files, freed {freed_mb:.2f} MB"
    )
    
    return deleted_count, freed_bytes
