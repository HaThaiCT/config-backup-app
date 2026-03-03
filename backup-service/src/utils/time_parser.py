"""Time duration parser for DD:HH:MM:SS format."""

import re
from typing import Union


def parse_duration(duration_str: str) -> int:
    """
    Parse duration string in DD:HH:MM:SS format to total seconds.
    
    Args:
        duration_str: Duration in format "DD:HH:MM:SS"
                     Examples: "01:00:00:00" (1 day), "00:06:00:00" (6 hours)
    
    Returns:
        Total seconds as integer
    
    Raises:
        ValueError: If format is invalid
    """
    pattern = r"^(\d{1,3}):(\d{2}):(\d{2}):(\d{2})$"
    match = re.match(pattern, duration_str.strip())
    
    if not match:
        raise ValueError(
            f"Invalid duration format: '{duration_str}'. "
            f"Expected format: DD:HH:MM:SS (e.g., '01:00:00:00' for 1 day)"
        )
    
    days, hours, minutes, seconds = map(int, match.groups())
    
    # Validate ranges
    if hours > 23:
        raise ValueError(f"Hours must be 0-23, got {hours}")
    if minutes > 59:
        raise ValueError(f"Minutes must be 0-59, got {minutes}")
    if seconds > 59:
        raise ValueError(f"Seconds must be 0-59, got {seconds}")
    
    total_seconds = (
        days * 86400 +      # 24 * 60 * 60
        hours * 3600 +      # 60 * 60
        minutes * 60 +
        seconds
    )
    
    if total_seconds == 0:
        raise ValueError("Duration must be greater than 0")
    
    return total_seconds


def format_duration(seconds: int) -> str:
    """
    Format seconds to human-readable string.
    
    Args:
        seconds: Total seconds
    
    Returns:
        Human-readable string like "1 day, 2 hours, 30 minutes"
    """
    if seconds < 0:
        raise ValueError("Seconds must be non-negative")
    
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if secs > 0 or not parts:
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")
    
    return ", ".join(parts)


def seconds_to_duration_str(seconds: int) -> str:
    """
    Convert seconds back to DD:HH:MM:SS format.
    
    Args:
        seconds: Total seconds
    
    Returns:
        Duration string in DD:HH:MM:SS format
    """
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    
    return f"{days:02d}:{hours:02d}:{minutes:02d}:{secs:02d}"
