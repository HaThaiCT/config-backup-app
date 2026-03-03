# Ubuntu Backup Service

Service tự động backup các file cấu hình trên Ubuntu Server với khả năng lên lịch, cleanup tự động và hỗ trợ multi-config.

---

## Mục lục

1. [Quick Start với Docker](#quick-start-với-docker)
2. [Hướng dẫn cài đặt chi tiết](#hướng-dẫn-cài-đặt-chi-tiết)
   - [Docker](#option-1-docker)
   - [Ubuntu Systemd](#option-2-ubuntu-systemd-production)
3. [Tài liệu kiến trúc](#tài-liệu-kiến-trúc)
   - [Vấn đề cần giải quyết](#vấn-đề-cần-giải-quyết)
   - [Tech Stack](#tech-stack)
   - [Cấu trúc dự án](#cấu-trúc-dự-án)
   - [Luồng hoạt động](#luồng-hoạt-động)
4. [Cấu hình](#cấu-hình)
5. [CLI Commands](#cli-commands)

---

## Quick Start với Docker

### Build và Test nhanh (< 5 phút)

```powershell
# 1. Clone repository
git clone https://github.com/your-org/backup-service.git
cd backup-service

# 2. Build Docker image
cd docker
docker-compose build

# 3. Khởi động container
docker-compose up -d

# 4. Kiểm tra logs (xác nhận service đang chạy)
docker logs backup-service

# 5. Test manual backup
docker exec backup-service python -m src.main --backup

# 6. Xem kết quả backup
docker exec backup-service ls -la /backups/

# 7. Dừng container khi test xong
docker-compose down
```

### Kết quả mong đợi

```
Backup Service Started (Multi-Config Mode)
Loaded 2 configuration(s)
[app] Backup interval: 7 minutes
[system] Backup interval: 5 minutes
Scheduler running. Press Ctrl+C to stop.
```

---

## Hướng dẫn cài đặt chi tiết

### Option 1: Docker

#### Yêu cầu
- Docker 20.10+
- Docker Compose 2.0+

#### Bước 1: Clone repository

```bash
git clone https://github.com/your-org/backup-service.git
cd backup-service
```

#### Bước 2: Cấu hình

**Single config (đơn giản):**
```bash
# Copy và chỉnh sửa config mẫu
cp config/config.example.yaml config/config.docker.yaml
nano config/config.docker.yaml
```

**Multi-config (nâng cao):**
```bash
# Tạo thư mục conf.d và các file config
mkdir -p docker/conf.d

# Tạo config cho nginx
cat > docker/conf.d/nginx.yaml << 'EOF'
name: nginx
backup:
  source_files:
    - /etc/nginx/
  destination: /backups
schedule:
  backup_interval: "01:00:00:00"
  cleanup_interval: "01:00:00:00"
cleanup:
  ttl: "30:00:00:00"
  min_keep: 5
EOF
```

#### Bước 3: Chỉnh sửa docker-compose.yml (nếu cần)

```yaml
volumes:
  # Mount thư mục cần backup từ host
  - /etc/nginx:/etc/nginx:ro
  - /etc/ssh:/etc/ssh:ro
  
  # Multi-config (uncomment nếu dùng conf.d)
  - ./conf.d:/etc/backup-service/conf.d:ro
```

#### Bước 4: Build và chạy

```bash
cd docker
docker-compose build
docker-compose up -d
```

#### Bước 5: Kiểm tra

```bash
# Xem logs
docker logs -f backup-service

# Manual backup
docker exec backup-service python -m src.main --backup

# Vào shell container
docker exec -it backup-service /bin/sh
```

#### Quản lý Docker

| Lệnh | Mô tả |
|------|-------|
| `docker-compose up -d` | Khởi động |
| `docker-compose down` | Dừng |
| `docker-compose logs -f` | Xem logs real-time |
| `docker-compose restart` | Khởi động lại |
| `docker exec backup-service python -m src.main --backup` | Backup ngay |

---

### Option 2: Ubuntu Systemd (Production)

#### Yêu cầu
- Ubuntu 20.04+ (hoặc Debian-based)
- Python 3.10+
- Root access

#### Bước 1: Clone repository

```bash
git clone https://github.com/your-org/backup-service.git
cd backup-service
```

#### Bước 2: Chạy script cài đặt

```bash
sudo ./scripts/install.sh
```

Script sẽ tự động:
- Tạo virtual environment tại `/opt/backup-service/`
- Cài đặt dependencies
- Copy config mẫu sang `/etc/backup-service/`
- Cài đặt systemd service

#### Bước 3: Cấu hình

**Single config:**
```bash
sudo nano /etc/backup-service/config.yaml
```

**Multi-config:**
```bash
# Tạo thư mục conf.d
sudo mkdir -p /etc/backup-service/conf.d

# Tạo config cho từng nhóm file
sudo nano /etc/backup-service/conf.d/nginx.yaml
sudo nano /etc/backup-service/conf.d/mysql.yaml
```

#### Bước 4: Enable và start service

```bash
sudo systemctl enable backup-service
sudo systemctl start backup-service
```

#### Bước 5: Kiểm tra

```bash
# Check status
sudo systemctl status backup-service

# Xem logs
sudo journalctl -u backup-service -f

# Manual backup
sudo /opt/backup-service/venv/bin/python -m src.main --backup
```

#### Quản lý Systemd

| Lệnh | Mô tả |
|------|-------|
| `sudo systemctl start backup-service` | Khởi động |
| `sudo systemctl stop backup-service` | Dừng |
| `sudo systemctl restart backup-service` | Khởi động lại |
| `sudo systemctl status backup-service` | Kiểm tra trạng thái |
| `sudo journalctl -u backup-service -f` | Xem logs |

#### Gỡ cài đặt

```bash
sudo ./scripts/uninstall.sh
```

---

## Tài liệu kiến trúc

### Vấn đề cần giải quyết

**Bối cảnh:**
Trong môi trường production, các file cấu hình hệ thống (nginx, SSH, MySQL, etc.) rất quan trọng. Việc mất hoặc hỏng các file này có thể dẫn đến:
- Downtime kéo dài
- Mất cấu hình đã tối ưu
- Khó khăn trong việc khôi phục hệ thống

**Giải pháp:**
Backup Service cung cấp:
1. **Backup tự động** - Không cần can thiệp thủ công
2. **Cleanup thông minh** - Tự động xóa backup cũ theo TTL, giữ lại số lượng tối thiểu
3. **Multi-config** - Backup nhiều nhóm file với schedule khác nhau
4. **Nén hiệu quả** - tar.gz giảm dung lượng lưu trữ
5. **Đa nền tảng** - Chạy trên Docker hoặc systemd

---

### Tech Stack

| Công nghệ | Version | Lý do lựa chọn |
|-----------|---------|----------------|
| **Python** | 3.10+ | Ngôn ngữ scripting mạnh mẽ, cross-platform, có sẵn trên Ubuntu. Ecosystem phong phú cho system administration |
| **PyYAML** | 6.0+ | Parser YAML chuẩn cho Python. YAML được chọn vì human-readable hơn JSON, phù hợp cho config files |
| **Pydantic** | 2.0+ | Validation mạnh mẽ với type hints. Tự động validate config khi load, báo lỗi rõ ràng |
| **APScheduler** | 3.10+ | Scheduler background đáng tin cậy. Hỗ trợ interval triggers, job persistence, graceful shutdown |
| **tarfile** | built-in | Module chuẩn của Python để tạo tar.gz. Không cần dependency ngoài |
| **Docker** | 20.10+ | Container hóa ứng dụng. Dễ deploy, isolate environment, reproducible |
| **systemd** | - | Init system chuẩn của Ubuntu. Auto-restart, logging tích hợp |

**Tại sao không dùng:**
- **Bash script**: Khó maintain, thiếu validation, không có scheduling tốt
- **Cron + rsync**: Không có cleanup logic, khó monitor
- **Go/Rust**: Overkill cho task này, Python đủ nhanh và dễ extend

---

### Cấu trúc dự án

```
backup-service/
│
├── src/                          # Source code chính
│   ├── __init__.py
│   ├── __main__.py               # Entry point: python -m src
│   ├── main.py                   # Main logic, setup logging, start scheduler
│   ├── cli.py                    # Argument parser (--help, --version, --backup)
│   ├── config.py                 # Load & validate YAML config (Pydantic models)
│   ├── backup.py                 # Tạo tar.gz backup
│   ├── cleanup.py                # Xóa backup cũ theo TTL
│   ├── scheduler.py              # APScheduler setup, job management
│   └── utils/
│       └── time_parser.py        # Parse format DD:HH:MM:SS
│
├── config/                       # Config files
│   ├── config.yaml               # Config chính
│   ├── config.example.yaml       # Config mẫu
│   ├── config.docker.yaml        # Config cho Docker
│   └── conf.d/                   # Multi-config directory
│       ├── nginx.yaml
│       ├── mysql.yaml
│       └── ssh.yaml
│
├── docker/                       # Docker files
│   ├── Dockerfile                # Multi-stage build
│   ├── docker-compose.yml
│   └── conf.d/                   # Docker-specific configs
│       ├── app.yaml
│       └── system.yaml
│
├── systemd/                      # Systemd files
│   └── backup-service.service
│
├── scripts/                      # Install/uninstall scripts
│   ├── install.sh
│   └── uninstall.sh
│
├── tests/                        # Unit tests
│   ├── test_backup.py
│   ├── test_cleanup.py
│   ├── test_config.py
│   └── test_time_parser.py
│
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Dev dependencies (pytest, etc.)
├── setup.cfg                     # Pytest config
└── README.md
```

#### Files/Paths quan trọng

| Path | Mô tả |
|------|-------|
| `src/main.py` | Entry point, orchestrates all modules |
| `src/config.py` | Config loading, validation, multi-config support |
| `src/scheduler.py` | APScheduler setup, MultiConfigScheduler class |
| `src/backup.py` | tar.gz creation logic |
| `src/cleanup.py` | TTL-based cleanup logic |
| `/etc/backup-service/config.yaml` | Config file (systemd) |
| `/etc/backup-service/conf.d/` | Multi-config directory |
| `/backups/` | Backup destination |
| `/var/log/backup-service/` | Log files |

---

### Luồng hoạt động

#### 1. Khởi động (Startup Flow)

```
┌─────────────────┐
│   main.py       │
│   Entry Point   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│   cli.py        │────▶│ --backup flag?   │
│   Parse args    │     │ Yes: run & exit  │
└────────┬────────┘     └──────────────────┘
         │ No
         ▼
┌─────────────────┐     ┌──────────────────┐
│   config.py     │────▶│ conf.d exists?   │
│   Load config   │     │ Yes: load all    │
└────────┬────────┘     │ No: single config│
         │              └──────────────────┘
         ▼
┌─────────────────┐
│   scheduler.py  │
│   Start jobs    │
│   - Backup jobs │
│   - Cleanup jobs│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Running...    │
│   Wait for jobs │
└─────────────────┘
```

#### 2. Backup Flow

```
┌─────────────────┐
│ Scheduler       │
│ Trigger backup  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ backup.py       │
│ validate_files()│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ create_backup() │
│ - Generate name │
│ - Create tar.gz │
│ - Add files     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Output:         │
│ {name}_{date}.  │
│ tar.gz          │
└─────────────────┘
```

#### 3. Cleanup Flow

```
┌─────────────────┐
│ Scheduler       │
│ Trigger cleanup │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ cleanup.py      │
│ list backups    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Sort by date    │
│ Keep min_keep   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Check TTL       │
│ Delete expired  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Log results     │
│ freed space     │
└─────────────────┘
```

#### 4. Multi-Config Flow

```
                    ┌─────────────────┐
                    │ Load conf.d/    │
                    │ *.yaml files    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ nginx.yaml      │ │ mysql.yaml      │ │ ssh.yaml        │
│ interval: 1d    │ │ interval: 6h    │ │ interval: 7d    │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Backup Job:     │ │ Backup Job:     │ │ Backup Job:     │
│ nginx           │ │ mysql           │ │ ssh             │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│ /backups/                                               │
│ ├── nginx_20260303_020000.tar.gz                        │
│ ├── mysql_20260303_080000.tar.gz                        │
│ └── ssh_20260310_020000.tar.gz                          │
└─────────────────────────────────────────────────────────┘
```

---

## Cấu hình

### Config file mẫu

```yaml
# Tên config (dùng làm prefix cho backup file)
name: nginx

# Backup settings
backup:
  source_files:
    - /etc/nginx/nginx.conf
    - /etc/nginx/sites-available/
    - /etc/nginx/sites-enabled/
  destination: /backups

# Schedule (format: DD:HH:MM:SS)
schedule:
  backup_interval: "01:00:00:00"    # 1 ngày
  cleanup_interval: "01:00:00:00"   # 1 ngày

# Cleanup settings
cleanup:
  ttl: "30:00:00:00"                # Xóa backup > 30 ngày
  min_keep: 5                       # Luôn giữ ít nhất 5 bản

# Logging
logging:
  level: INFO                       # DEBUG, INFO, WARNING, ERROR
  file: /var/log/backup-service/nginx.log
  max_size_mb: 10
  backup_count: 5
```

### Time Format

Format: `DD:HH:MM:SS` (Days:Hours:Minutes:Seconds)

| Giá trị | Ý nghĩa |
|---------|---------|
| `00:00:05:00` | 5 phút |
| `00:00:30:00` | 30 phút |
| `00:01:00:00` | 1 giờ |
| `00:06:00:00` | 6 giờ |
| `01:00:00:00` | 1 ngày |
| `07:00:00:00` | 7 ngày |
| `30:00:00:00` | 30 ngày |

---

## CLI Commands

```bash
# Hiển thị help
python -m src.main --help

# Hiển thị version
python -m src.main --version

# Backup ngay lập tức (chạy xong thoát)
python -m src.main --backup

# Chạy daemon mode (scheduler)
python -m src.main
```

---

## License

MIT License
