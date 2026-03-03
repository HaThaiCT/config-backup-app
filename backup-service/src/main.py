"""Main entry point for backup service."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List

from .cli import parse_args
from .config import load_config, load_all_configs, get_merged_logging_config, Config
from .backup import run_backup
from .scheduler import start_scheduler, start_multi_scheduler
from .utils.time_parser import format_duration


def setup_logging(config: Config):
    """
    Setup logging configuration.
    
    Args:
        config: Configuration object
    """
    log_config = config.logging
    log_level = getattr(logging, log_config.level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if configured)
    if log_config.file:
        log_path = Path(log_config.file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            filename=log_path,
            maxBytes=log_config.max_size_mb * 1024 * 1024,
            backupCount=log_config.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def main():
    """Main entry point."""
    # Parse command-line arguments
    args = parse_args()
    
    # Setup basic logging first (before config is loaded)
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Load all configurations (from conf.d or single config.yaml)
        configs = load_all_configs()
        
        # Setup logging with first config's settings
        log_config = get_merged_logging_config(configs)
        setup_logging(Config(
            backup={"source_files": ["/tmp"]},  # Dummy for logging setup
            logging=log_config.model_dump()
        ))
        logger = logging.getLogger(__name__)
        
        # Handle --backup flag
        if args.backup:
            logger.info(f"Manual backup requested for {len(configs)} config(s)")
            all_success = True
            for config in configs:
                logger.info(f"Backing up: {config.name}")
                success = run_backup(config)
                if not success:
                    all_success = False
            sys.exit(0 if all_success else 1)
        
        # Default: start scheduler (daemon mode)
        start_multi_scheduler(configs)
    
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
