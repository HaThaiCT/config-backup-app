# ──────────────────────────────────────────────
# Build image demo config-backup trên Ubuntu 24.04
# ──────────────────────────────────────────────
FROM ubuntu:24.04

# Tránh prompt tương tác khi cài apt
ENV DEBIAN_FRONTEND=noninteractive

# Cài Python 3.12, pipx, và các công cụ cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.12 \
        python3-pip \
        python3-venv \
        pipx \
        # Tạo thư mục backup mẫu để demo
        && mkdir -p /backups /etc/demo-configs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Đưa pipx vào PATH
ENV PATH="/root/.local/bin:$PATH"
RUN pipx ensurepath

# Copy toàn bộ source code vào image
WORKDIR /app
COPY . .

# Cài tool bằng pipx
RUN pipx install .

# Tạo các file cấu hình demo để backup
RUN echo "server_name demo-server;" > /etc/demo-configs/nginx.conf \
    && echo "Port 22\nPermitRootLogin yes" > /etc/demo-configs/sshd_config \
    && echo "0 2 * * * root config-backup backup" > /etc/demo-configs/crontab \
    && mkdir -p /etc/demo-configs/app && echo '{"env":"production","port":8080}' > /etc/demo-configs/app/settings.json

# Copy config.yaml demo (override đường dẫn sources cho môi trường container)
COPY docker/config.demo.yaml /app/config.demo.yaml

# Thư mục lưu backup và log
VOLUME ["/backups", "/var/log/config-backup"]

CMD ["/bin/bash"]
