"""Scheduler for periodic backup and cleanup tasks."""

import logging
import signal
import sys
from typing import Callable, List

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import Config
from .backup import run_backup
from .cleanup import run_cleanup
from .utils.time_parser import format_duration

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Scheduler for backup service tasks."""
    
    def __init__(self, config: Config):
        """
        Initialize scheduler with configuration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.scheduler = BlockingScheduler()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers."""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received {sig_name}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def _backup_job(self):
        """Wrapper for backup job."""
        logger.info("Running scheduled backup...")
        try:
            run_backup(self.config)
        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")
    
    def _cleanup_job(self):
        """Wrapper for cleanup job."""
        logger.info("Running scheduled cleanup...")
        try:
            run_cleanup(self.config)
        except Exception as e:
            logger.error(f"Scheduled cleanup failed: {e}")
    
    def start(self):
        """
        Start the scheduler with configured jobs.
        
        This method blocks until the scheduler is stopped.
        """
        backup_interval = self.config.schedule.backup_interval_seconds
        cleanup_interval = self.config.schedule.cleanup_interval_seconds
        
        # Add backup job
        self.scheduler.add_job(
            self._backup_job,
            trigger=IntervalTrigger(seconds=backup_interval),
            id="backup_job",
            name="Backup Job",
            max_instances=1,
            coalesce=True,
        )
        
        # Add cleanup job
        self.scheduler.add_job(
            self._cleanup_job,
            trigger=IntervalTrigger(seconds=cleanup_interval),
            id="cleanup_job",
            name="Cleanup Job",
            max_instances=1,
            coalesce=True,
        )
        
        logger.info("=" * 60)
        logger.info("Backup Service Started")
        logger.info("=" * 60)
        logger.info(f"Backup interval: {format_duration(backup_interval)}")
        logger.info(f"Cleanup interval: {format_duration(cleanup_interval)}")
        logger.info(f"Cleanup TTL: {format_duration(self.config.cleanup.ttl_seconds)}")
        logger.info(f"Min backups to keep: {self.config.cleanup.min_keep}")
        logger.info(f"Backup destination: {self.config.backup.destination}")
        logger.info("=" * 60)
        logger.info("Scheduler running. Press Ctrl+C to stop.")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")


class MultiConfigScheduler:
    """Scheduler for multiple backup configurations."""
    
    def __init__(self, configs: List[Config]):
        """
        Initialize scheduler with multiple configurations.
        
        Args:
            configs: List of configuration objects
        """
        self.configs = configs
        self.scheduler = BlockingScheduler()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers."""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received {sig_name}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def _create_backup_job(self, config: Config):
        """Create a backup job function for a specific config."""
        def backup_job():
            logger.info(f"[{config.name}] Running scheduled backup...")
            try:
                run_backup(config)
            except Exception as e:
                logger.error(f"[{config.name}] Scheduled backup failed: {e}")
        return backup_job
    
    def _create_cleanup_job(self, config: Config):
        """Create a cleanup job function for a specific config."""
        def cleanup_job():
            logger.info(f"[{config.name}] Running scheduled cleanup...")
            try:
                run_cleanup(config)
            except Exception as e:
                logger.error(f"[{config.name}] Scheduled cleanup failed: {e}")
        return cleanup_job
    
    def start(self):
        """
        Start the scheduler with all configured jobs.
        
        This method blocks until the scheduler is stopped.
        """
        logger.info("=" * 60)
        logger.info("Backup Service Started (Multi-Config Mode)")
        logger.info("=" * 60)
        logger.info(f"Loaded {len(self.configs)} configuration(s)")
        logger.info("")
        
        for config in self.configs:
            backup_interval = config.schedule.backup_interval_seconds
            cleanup_interval = config.schedule.cleanup_interval_seconds
            
            # Add backup job for this config
            self.scheduler.add_job(
                self._create_backup_job(config),
                trigger=IntervalTrigger(seconds=backup_interval),
                id=f"backup_{config.name}",
                name=f"Backup: {config.name}",
                max_instances=1,
                coalesce=True,
            )
            
            # Add cleanup job for this config
            self.scheduler.add_job(
                self._create_cleanup_job(config),
                trigger=IntervalTrigger(seconds=cleanup_interval),
                id=f"cleanup_{config.name}",
                name=f"Cleanup: {config.name}",
                max_instances=1,
                coalesce=True,
            )
            
            logger.info(f"[{config.name}]")
            logger.info(f"  Backup interval: {format_duration(backup_interval)}")
            logger.info(f"  Cleanup interval: {format_duration(cleanup_interval)}")
            logger.info(f"  TTL: {format_duration(config.cleanup.ttl_seconds)}")
            logger.info(f"  Destination: {config.backup.destination}")
            logger.info(f"  Sources: {len(config.backup.source_files)} file(s)")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("Scheduler running. Press Ctrl+C to stop.")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")


def start_scheduler(config: Config):
    """
    Start the backup scheduler with single config.
    
    Args:
        config: Configuration object
    """
    scheduler = BackupScheduler(config)
    scheduler.start()


def start_multi_scheduler(configs: List[Config]):
    """
    Start the backup scheduler with multiple configs.
    
    Args:
        configs: List of configuration objects
    """
    if len(configs) == 1:
        # Use single-config scheduler for backward compatibility
        start_scheduler(configs[0])
    else:
        scheduler = MultiConfigScheduler(configs)
        scheduler.start()
