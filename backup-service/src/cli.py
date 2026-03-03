"""Command-line interface for backup service."""

import argparse
import sys
from . import __version__


def parse_args(args=None) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: Arguments to parse (default: sys.argv[1:])
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="backup-service",
        description="Ubuntu Backup Service - Automatic configuration file backup",
        epilog="Config file location: /etc/backup-service/config.yaml (or $BACKUP_CONFIG)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version and exit",
    )
    
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Run backup immediately and exit",
    )
    
    return parser.parse_args(args)


def main():
    """CLI entry point."""
    args = parse_args()
    return args


if __name__ == "__main__":
    main()
