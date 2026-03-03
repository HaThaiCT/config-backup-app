# =============================================================================
# SAMPLE CONF.D CONFIGURATION
# =============================================================================
# 
# Thư mục conf.d/ chứa nhiều file config riêng biệt.
# Mỗi file .yaml sẽ được load và chạy như một backup job độc lập.
#
# Cấu trúc:
#   conf.d/
#   ├── nginx.yaml     → Backup nginx configs
#   ├── ssh.yaml       → Backup SSH configs  
#   ├── mysql.yaml     → Backup MySQL configs
#   └── custom.yaml    → Backup custom files
#
# Mỗi file có thể có interval và TTL riêng.
# Filename (không có extension) sẽ được dùng làm prefix cho backup file.
#
# Ví dụ output:
#   /backups/
#   ├── nginx_20260303_120000.tar.gz
#   ├── ssh_20260303_120000.tar.gz
#   └── mysql_20260303_120000.tar.gz
#
# =============================================================================
