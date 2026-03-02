"""
cli.py — Click CLI entry point

Subcommands:
    backup         Chạy backup ngay lập tức
    list           Liệt kê các bản backup hiện có
    install-timer  Cài đặt systemd timer tự động backup theo schedule.interval
    remove-timer   Gỡ bỏ systemd timer
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from . import backup as bk
from . import config as cfg

UNIT_NAME = "config-backup"


# ──────────────────────────────────────────────────────────────
# CLI Group
# ──────────────────────────────────────────────────────────────

@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.option(
    "--config", "-c",
    default="config.yaml",
    show_default=True,
    type=click.Path(),
    help="Đường dẫn tới file cấu hình config.yaml",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Mô phỏng thao tác, không thực sự ghi/xóa file",
)
@click.version_option("0.1.0", "-V", "--version")
@click.pass_context
def cli(ctx: click.Context, config: str, dry_run: bool) -> None:
    """
    \b
    config-backup — Công cụ tự động backup file cấu hình Ubuntu Server
    ─────────────────────────────────────────────────────────────────────
    Ví dụ sử dụng:
      config-backup backup
      config-backup backup --dry-run
      config-backup list
      config-backup install-timer
      config-backup remove-timer
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["dry_run"] = dry_run

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ──────────────────────────────────────────────────────────────
# Subcommand: backup
# ──────────────────────────────────────────────────────────────

@cli.command()
@click.pass_context
def backup(ctx: click.Context) -> None:
    """Chạy backup ngay: nén file vào destination, áp dụng retention."""
    config_path = ctx.obj["config_path"]
    dry_run = ctx.obj["dry_run"]

    # Load & validate config
    conf = cfg.load_config(config_path)

    # Khởi tạo logging
    logger = bk.setup_logging(cfg.get_log_file(conf), cfg.get_log_level(conf))
    logger.info("═" * 60)
    logger.info("Bắt đầu backup%s", " (DRY-RUN)" if dry_run else "")
    logger.info("Config: %s", Path(config_path).resolve())

    sources = cfg.get_sources(conf)
    destination = cfg.get_destination(conf)
    prefix = cfg.get_archive_prefix(conf)
    max_age_days, keep_last_n = cfg.get_retention(conf)

    # Tên file archive
    archive_name = bk.build_archive_name(prefix)
    archive_path = destination / archive_name

    logger.info("Archive: %s", archive_path)
    logger.info("Nguồn (%d):", len(sources))
    for s in sources:
        logger.info("  - %s", s)

    # Tạo archive
    try:
        added = bk.create_archive(archive_path, sources, dry_run=dry_run)
    except OSError:
        logger.error("Backup thất bại.")
        sys.exit(1)

    if not added:
        logger.warning("Không có file nào được backup (tất cả nguồn không tồn tại hoặc lỗi).")
    else:
        logger.info("Backup hoàn thành: %d nguồn được lưu.", len(added))

    # Áp dụng retention
    if max_age_days is not None or keep_last_n is not None:
        logger.info("Áp dụng retention policy...")
        bk.apply_retention(
            destination, prefix,
            max_age_days=max_age_days,
            keep_last_n=keep_last_n,
            dry_run=dry_run,
        )

    logger.info("Kết thúc.")


# ──────────────────────────────────────────────────────────────
# Subcommand: list
# ──────────────────────────────────────────────────────────────

@cli.command(name="list")
@click.pass_context
def list_backups(ctx: click.Context) -> None:
    """Liệt kê tất cả bản backup trong thư mục destination."""
    config_path = ctx.obj["config_path"]
    conf = cfg.load_config(config_path)

    destination = cfg.get_destination(conf)
    prefix = cfg.get_archive_prefix(conf)

    if not destination.exists():
        click.echo(f"Thư mục destination không tồn tại: {destination}")
        sys.exit(0)

    archives = sorted(
        destination.glob(f"{prefix}_*.tar.gz"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    if not archives:
        click.echo(f"Không có bản backup nào trong: {destination}")
        return

    click.echo(f"\n{'#':<4}  {'Tên file':<42}  {'Kích thước':>10}  {'Ngày tạo'}")
    click.echo("─" * 75)
    for i, f in enumerate(archives, start=1):
        size_mb = f.stat().st_size / 1_048_576
        from datetime import datetime
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        click.echo(f"{i:<4}  {f.name:<42}  {size_mb:>8.2f} MB  {mtime}")

    click.echo(f"\nTổng: {len(archives)} bản backup | Thư mục: {destination}\n")


# ──────────────────────────────────────────────────────────────
# Subcommand: install-timer
# ──────────────────────────────────────────────────────────────

@cli.command(name="install-timer")
@click.option(
    "--binary",
    default=None,
    type=click.Path(),
    help="Đường dẫn tới binary config-backup (mặc định: ~/.local/bin/config-backup)",
)
@click.pass_context
def install_timer(ctx: click.Context, binary: str | None) -> None:
    """Cài đặt systemd user timer để tự động backup theo schedule.interval trong config."""
    config_path = ctx.obj["config_path"]
    conf = cfg.load_config(config_path)

    logger = bk.setup_logging(cfg.get_log_file(conf), cfg.get_log_level(conf))

    interval = cfg.get_schedule_interval(conf)
    if interval is None:
        click.echo(
            "[LỖI] Chưa cấu hình schedule.interval trong config.yaml.\n"
            "Thêm ví dụ:\n\n"
            "  schedule:\n"
            '    interval: "01:00:00:00"   # mỗi 1 ngày\n',
            err=True,
        )
        sys.exit(1)

    span = bk.timedelta_to_systemd_span(interval)
    config_abs = Path(config_path).expanduser().resolve()
    binary_path = Path(binary).expanduser() if binary else None

    click.echo(f"Interval   : {span}")
    click.echo(f"Config     : {config_abs}")
    click.echo(f"Unit name  : {UNIT_NAME}")

    try:
        service_path, timer_path = bk.write_systemd_files(
            UNIT_NAME, span, config_abs, binary_path
        )
        bk.enable_timer(UNIT_NAME)
    except subprocess.CalledProcessError:
        click.echo("[LỖI] Không thể cài đặt timer. Kiểm tra log để biết chi tiết.", err=True)
        sys.exit(1)

    click.echo(f"\n✔ Timer đã được cài đặt thành công!")
    click.echo(f"  Service : {service_path}")
    click.echo(f"  Timer   : {timer_path}")
    click.echo(f"\nKiểm tra trạng thái:")
    click.echo(f"  systemctl --user status {UNIT_NAME}.timer")
    click.echo(f"  journalctl --user -u {UNIT_NAME}.service")


# ──────────────────────────────────────────────────────────────
# Subcommand: remove-timer
# ──────────────────────────────────────────────────────────────

@cli.command(name="remove-timer")
@click.confirmation_option(prompt="Bạn có chắc muốn gỡ bỏ systemd timer?")
@click.pass_context
def remove_timer(ctx: click.Context) -> None:
    """Gỡ bỏ systemd user timer đã cài đặt."""
    config_path = ctx.obj["config_path"]
    conf = cfg.load_config(config_path)
    logger = bk.setup_logging(cfg.get_log_file(conf), cfg.get_log_level(conf))

    systemd_dir = Path.home() / ".config" / "systemd" / "user"

    try:
        bk.disable_timer(UNIT_NAME)
    except Exception:
        click.echo("[CẢNH BÁO] Không thể disable timer (có thể chưa được enable).", err=True)

    # Xóa file .service và .timer
    for suffix in (".service", ".timer"):
        unit_file = systemd_dir / f"{UNIT_NAME}{suffix}"
        if unit_file.exists():
            unit_file.unlink()
            logger.info("Đã xóa: %s", unit_file)
            click.echo(f"  Đã xóa: {unit_file}")
        else:
            click.echo(f"  Không tìm thấy: {unit_file}")

    try:
        bk._systemctl("daemon-reload")
        click.echo("✔ Timer đã được gỡ bỏ thành công.")
    except Exception:
        click.echo("[CẢNH BÁO] daemon-reload thất bại.", err=True)


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli(obj={})
