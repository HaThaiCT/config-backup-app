"""
config.py — Đọc và validate file cấu hình config.yaml
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml


# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

REQUIRED_BACKUP_KEYS = ("sources", "destination", "archive_prefix")
MIN_INTERVAL_SECONDS = 60  # Tối thiểu 1 phút


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────

def load_config(path: str) -> dict[str, Any]:
    """Đọc config.yaml, trả về dict đã được validate đầy đủ."""
    config_path = Path(path).expanduser().resolve()

    if not config_path.exists():
        _abort(f"Không tìm thấy file cấu hình: {config_path}")

    with config_path.open(encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            _abort(f"Lỗi đọc YAML: {exc}")

    if not isinstance(data, dict):
        _abort("config.yaml không hợp lệ: nội dung phải là một mapping.")

    _validate_backup_section(data)
    _validate_retention_section(data)
    _validate_logging_section(data)
    _validate_schedule_section(data)

    return data


def get_sources(config: dict) -> list[Path]:
    """Trả về danh sách Path của các nguồn cần backup."""
    return [Path(s).expanduser() for s in config["backup"]["sources"]]


def get_destination(config: dict) -> Path:
    """Trả về thư mục đích."""
    return Path(config["backup"]["destination"]).expanduser()


def get_archive_prefix(config: dict) -> str:
    return config["backup"]["archive_prefix"]


def get_log_file(config: dict) -> Path:
    return Path(config["logging"]["log_file"]).expanduser()


def get_log_level(config: dict) -> str:
    return config["logging"].get("level", "INFO").upper()


def get_retention(config: dict) -> tuple[int | None, int | None]:
    """Trả về (max_age_days, keep_last_n). None nếu không cấu hình."""
    retention = config.get("retention") or {}
    return retention.get("max_age_days"), retention.get("keep_last_n")


def get_schedule_interval(config: dict) -> timedelta | None:
    """Trả về timedelta của schedule.interval, hoặc None nếu không cấu hình."""
    schedule = config.get("schedule") or {}
    raw = schedule.get("interval")
    if raw is None:
        return None
    return parse_interval(str(raw))


# ──────────────────────────────────────────────────────────────
# Parsing
# ──────────────────────────────────────────────────────────────

def parse_interval(s: str) -> timedelta:
    """
    Parse chuỗi dd:hh:mm:ss thành timedelta.

    Ví dụ:
        "07:02:30:00"  → timedelta(days=7, hours=2, minutes=30)
        "00:06:00:00"  → timedelta(hours=6)

    Raises:
        ValueError: nếu format sai, giá trị ngoài range, hoặc tổng < 60 giây.
    """
    parts = s.strip().split(":")
    if len(parts) != 4:
        raise ValueError(
            f"schedule.interval phải có format dd:hh:mm:ss, nhận được: {s!r}"
        )

    try:
        dd, hh, mm, ss = (int(p) for p in parts)
    except ValueError:
        raise ValueError(
            f"schedule.interval chứa ký tự không phải số: {s!r}"
        )

    if not (0 <= dd <= 99):
        raise ValueError(f"Ngày (dd) phải từ 0-99, nhận được: {dd}")
    if not (0 <= hh <= 23):
        raise ValueError(f"Giờ (hh) phải từ 0-23, nhận được: {hh}")
    if not (0 <= mm <= 59):
        raise ValueError(f"Phút (mm) phải từ 0-59, nhận được: {mm}")
    if not (0 <= ss <= 59):
        raise ValueError(f"Giây (ss) phải từ 0-59, nhận được: {ss}")

    td = timedelta(days=dd, hours=hh, minutes=mm, seconds=ss)

    if td.total_seconds() == 0:
        raise ValueError("schedule.interval không được là 00:00:00:00 (bằng 0).")
    if td.total_seconds() < MIN_INTERVAL_SECONDS:
        raise ValueError(
            f"schedule.interval quá nhỏ (tối thiểu {MIN_INTERVAL_SECONDS}s = 00:00:01:00)."
        )

    return td


# ──────────────────────────────────────────────────────────────
# Internal validators
# ──────────────────────────────────────────────────────────────

def _validate_backup_section(data: dict) -> None:
    backup = data.get("backup")
    if not isinstance(backup, dict):
        _abort("Thiếu section 'backup' trong config.yaml.")

    for key in REQUIRED_BACKUP_KEYS:
        if not backup.get(key):
            _abort(f"Thiếu hoặc rỗng: backup.{key}")

    if not isinstance(backup["sources"], list) or len(backup["sources"]) == 0:
        _abort("backup.sources phải là một danh sách có ít nhất 1 phần tử.")


def _validate_retention_section(data: dict) -> None:
    retention = data.get("retention")
    if retention is None:
        return  # Không bắt buộc

    if not isinstance(retention, dict):
        _abort("Section 'retention' phải là một mapping.")

    max_age = retention.get("max_age_days")
    keep_n = retention.get("keep_last_n")

    if max_age is not None and (not isinstance(max_age, int) or max_age <= 0):
        _abort("retention.max_age_days phải là số nguyên dương.")
    if keep_n is not None and (not isinstance(keep_n, int) or keep_n <= 0):
        _abort("retention.keep_last_n phải là số nguyên dương.")


def _validate_logging_section(data: dict) -> None:
    logging_cfg = data.get("logging")
    if logging_cfg is None:
        # Thiết lập giá trị mặc định
        data["logging"] = {
            "log_file": "~/.local/share/config-backup/backup.log",
            "level": "INFO",
        }
        return

    if not isinstance(logging_cfg, dict):
        _abort("Section 'logging' phải là một mapping.")

    if not logging_cfg.get("log_file"):
        _abort("logging.log_file không được để trống.")

    level = logging_cfg.get("level", "INFO").upper()
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if level not in valid_levels:
        _abort(f"logging.level không hợp lệ: {level!r}. Chọn: {valid_levels}")
    logging_cfg["level"] = level


def _validate_schedule_section(data: dict) -> None:
    schedule = data.get("schedule")
    if schedule is None:
        return  # Không bắt buộc

    if not isinstance(schedule, dict):
        _abort("Section 'schedule' phải là một mapping.")

    raw_interval = schedule.get("interval")
    if raw_interval is not None:
        try:
            parse_interval(str(raw_interval))
        except ValueError as exc:
            _abort(str(exc))


def _abort(message: str) -> None:
    print(f"[CONFIG ERROR] {message}", file=sys.stderr)
    sys.exit(1)
