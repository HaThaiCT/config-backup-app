"""
backup.py — Core logic: tạo archive, quản lý retention, logging, systemd timer
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import subprocess
import sys
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


# ──────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────

def setup_logging(log_file: Path, level: str = "INFO") -> logging.Logger:
    """
    Cấu hình logger ghi đồng thời ra file và stdout.

    - File handler: ghi từ DEBUG trở lên (rotating, max 5MB × 3 bản)
    - Stdout handler: ghi từ mức `level` trở lên
    """
    logger = logging.getLogger("config-backup")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Tạo thư mục chứa file log nếu chưa có
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # File handler — rotating 5MB × 3 bản
    fh = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Stdout handler
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(getattr(logging, level, logging.INFO))
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)

    return logger


# ──────────────────────────────────────────────────────────────
# Archive creation
# ──────────────────────────────────────────────────────────────

def build_archive_name(prefix: str) -> str:
    """Tạo tên file archive theo format: prefix_YYYYMMDD_HHMMSS.tar.gz"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.tar.gz"


def create_archive(
    output_path: Path,
    sources: list[Path],
    dry_run: bool = False,
) -> list[Path]:
    """
    Nén danh sách sources vào output_path (.tar.gz).

    - Bỏ qua file/thư mục không tồn tại, ghi warning.
    - dry_run=True: chỉ in ra thao tác, không tạo file thực.

    Returns:
        Danh sách các path đã được thêm thành công vào archive.
    """
    logger = logging.getLogger("config-backup")
    added: list[Path] = []

    if dry_run:
        logger.info("[DRY-RUN] Sẽ tạo archive: %s", output_path)
        for src in sources:
            if src.exists():
                logger.info("[DRY-RUN]   + %s", src)
                added.append(src)
            else:
                logger.warning("[DRY-RUN]   ✗ Bỏ qua (không tồn tại): %s", src)
        return added

    # Tạo thư mục đích nếu chưa có
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(output_path, "w:gz", compresslevel=6) as tar:
            for src in sources:
                if not src.exists():
                    logger.warning("Bỏ qua (không tồn tại): %s", src)
                    continue
                try:
                    tar.add(str(src), arcname=src.name, recursive=True)
                    logger.info("  + Đã thêm: %s", src)
                    added.append(src)
                except PermissionError:
                    logger.warning("Bỏ qua (không có quyền đọc): %s", src)
                except OSError as exc:
                    logger.warning("Bỏ qua (lỗi I/O): %s — %s", src, exc)
    except OSError as exc:
        logger.error("Không thể tạo archive %s: %s", output_path, exc)
        # Xóa file archive dở nếu có
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        raise

    logger.info("Archive đã tạo: %s (%.2f MB)", output_path, output_path.stat().st_size / 1_048_576)
    return added


# ──────────────────────────────────────────────────────────────
# Retention management
# ──────────────────────────────────────────────────────────────

def apply_retention(
    backup_dir: Path,
    prefix: str,
    max_age_days: Optional[int] = None,
    keep_last_n: Optional[int] = None,
    dry_run: bool = False,
) -> None:
    """
    Áp dụng chính sách giữ/xóa backup:
    1. Xóa file cũ hơn max_age_days (nếu được cấu hình).
    2. Xóa file dư nếu tổng số vượt quá keep_last_n (nếu được cấu hình).

    Thứ tự: xóa theo tuổi trước, rồi mới giới hạn số lượng.
    """
    logger = logging.getLogger("config-backup")

    if max_age_days is None and keep_last_n is None:
        return  # Không cấu hình retention → không làm gì

    pattern = f"{prefix}_*.tar.gz"
    archives = sorted(
        backup_dir.glob(pattern),
        key=lambda f: f.stat().st_mtime,
    )  # cũ nhất trước

    # Bước 1: xóa theo tuổi
    if max_age_days is not None:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=max_age_days)
        remaining: list[Path] = []
        for f in archives:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                _delete_backup(f, reason=f"tuổi > {max_age_days} ngày", dry_run=dry_run)
            else:
                remaining.append(f)
        archives = remaining

    # Bước 2: giới hạn số lượng
    if keep_last_n is not None and len(archives) > keep_last_n:
        to_delete = archives[: len(archives) - keep_last_n]  # các bản cũ nhất
        for f in to_delete:
            _delete_backup(f, reason=f"vượt quá keep_last_n={keep_last_n}", dry_run=dry_run)


def _delete_backup(f: Path, reason: str, dry_run: bool) -> None:
    logger = logging.getLogger("config-backup")
    prefix = "[DRY-RUN] " if dry_run else ""
    logger.info("%sXóa backup (%s): %s", prefix, reason, f.name)
    if not dry_run:
        try:
            f.unlink()
        except OSError as exc:
            logger.warning("Không thể xóa %s: %s", f.name, exc)


# ──────────────────────────────────────────────────────────────
# systemd integration
# ──────────────────────────────────────────────────────────────

def timedelta_to_systemd_span(td: timedelta) -> str:
    """
    Chuyển timedelta thành chuỗi thời gian systemd.

    Ví dụ:
        timedelta(days=7, hours=2, minutes=30) → "7d 2h 30min"
        timedelta(hours=6)                     → "6h"
    """
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}min")
    if seconds:
        parts.append(f"{seconds}s")

    return " ".join(parts) if parts else "0s"


def write_systemd_files(
    unit_name: str,
    span: str,
    config_path: Path,
    binary_path: Optional[Path] = None,
) -> tuple[Path, Path]:
    """
    Ghi file .service và .timer vào ~/.config/systemd/user/.
    Sau đó reload systemd user daemon.

    Args:
        unit_name:   Tên unit (vd: "config-backup")
        span:        Chuỗi systemd time span (vd: "7d 2h 30min")
        config_path: Đường dẫn tới config.yaml
        binary_path: Đường dẫn tới binary config-backup (mặc định: ~/.local/bin/config-backup)

    Returns:
        Tuple (service_path, timer_path)
    """
    logger = logging.getLogger("config-backup")
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)

    if binary_path is None:
        binary_path = Path.home() / ".local" / "bin" / unit_name

    service_path = systemd_dir / f"{unit_name}.service"
    timer_path = systemd_dir / f"{unit_name}.timer"

    # ── .service ──
    service_content = f"""\
[Unit]
Description=Config Backup Tool — {unit_name}
After=network.target

[Service]
Type=oneshot
ExecStart={binary_path} backup --config {config_path}
Environment=PATH=/usr/local/bin:/usr/bin:/bin:{Path.home() / ".local/bin"}
StandardOutput=journal
StandardError=journal
"""

    # ── .timer ──
    timer_content = f"""\
[Unit]
Description=Config Backup Timer — chạy mỗi {span}

[Timer]
OnBootSec=1min
OnUnitActiveSec={span}
AccuracySec=1s
Persistent=true

[Install]
WantedBy=timers.target
"""

    # Atomic write
    for path, content in [(service_path, service_content), (timer_path, timer_content)]:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        os.chmod(tmp, 0o644)
        tmp.rename(path)
        logger.info("Đã ghi: %s", path)

    # Reload daemon
    _systemctl("daemon-reload")
    logger.info("systemd user daemon đã reload.")

    return service_path, timer_path


def enable_timer(unit_name: str) -> None:
    """Enable và start systemd user timer."""
    logger = logging.getLogger("config-backup")
    _systemctl("enable", "--now", f"{unit_name}.timer")
    logger.info("Timer '%s.timer' đã được enable và start.", unit_name)


def disable_timer(unit_name: str) -> None:
    """Disable và stop systemd user timer."""
    logger = logging.getLogger("config-backup")
    _systemctl("disable", "--now", f"{unit_name}.timer")
    logger.info("Timer '%s.timer' đã được disable.", unit_name)


def _systemctl(*args: str) -> subprocess.CompletedProcess:
    """Chạy lệnh systemctl --user với error handling."""
    logger = logging.getLogger("config-backup")
    cmd = ["systemctl", "--user", *args]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        return result
    except subprocess.CalledProcessError as exc:
        logger.error("Lệnh thất bại: %s\nStderr: %s", " ".join(cmd), exc.stderr)
        raise
    except FileNotFoundError:
        logger.error("Không tìm thấy 'systemctl'. Công cụ này yêu cầu Ubuntu với systemd.")
        sys.exit(1)
