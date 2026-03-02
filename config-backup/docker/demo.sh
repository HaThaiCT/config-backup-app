#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# demo.sh — Script chạy demo từng bước trong container
# Chạy bằng: bash /app/docker/demo.sh
# ─────────────────────────────────────────────────────────────

set -euo pipefail

CONFIG="/app/config.demo.yaml"
BINARY="config-backup"

# Màu sắc
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RESET='\033[0m'

step() { echo -e "\n${CYAN}━━━ $1 ${RESET}"; }
ok()   { echo -e "${GREEN}✔ $1${RESET}"; }
info() { echo -e "${YELLOW}ℹ $1${RESET}"; }

# ── Bước 1: Kiểm tra cài đặt ────────────────────────────────
step "Bước 1: Kiểm tra cài đặt"
which $BINARY && ok "config-backup đã cài đặt thành công"
$BINARY --version

# ── Bước 2: Xem help ────────────────────────────────────────
step "Bước 2: Xem --help"
$BINARY --help

# ── Bước 3: Dry-run (mô phỏng, không tạo file) ─────────────
step "Bước 3: Dry-run (mô phỏng)"
$BINARY --config "$CONFIG" --dry-run backup

# ── Bước 4: Backup thật lần 1 ───────────────────────────────
step "Bước 4: Chạy backup thật (lần 1)"
$BINARY --config "$CONFIG" backup
ok "Backup lần 1 hoàn thành"

# ── Bước 5: Backup thật lần 2 ───────────────────────────────
step "Bước 5: Chạy backup thật (lần 2)"
sleep 2
$BINARY --config "$CONFIG" backup
ok "Backup lần 2 hoàn thành"

# ── Bước 6: Liệt kê danh sách backup ────────────────────────
step "Bước 6: Liệt kê danh sách backup"
$BINARY --config "$CONFIG" list

# ── Bước 7: Kiểm tra file backup ────────────────────────────
step "Bước 7: Xem nội dung file .tar.gz"
LATEST=$(ls -t /backups/backup_*.tar.gz 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
    info "File backup: $LATEST"
    tar -tzvf "$LATEST"
    ok "Archive hợp lệ!"
fi

# ── Bước 8: Xem file log ────────────────────────────────────
step "Bước 8: Xem file log"
LOG_FILE="/var/log/config-backup/backup.log"
if [ -f "$LOG_FILE" ]; then
    cat "$LOG_FILE"
    ok "Log ghi thành công"
else
    info "Log file chưa có (có thể đường dẫn khác)"
fi

echo -e "\n${GREEN}═══════════════════════════════════════${RESET}"
echo -e "${GREEN}  Demo hoàn thành! Tất cả tính năng OK  ${RESET}"
echo -e "${GREEN}═══════════════════════════════════════${RESET}\n"
