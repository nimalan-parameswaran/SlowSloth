#!/usr/bin/env bash
# SlowSloth Deployment and Environment Setup Script for Arduino UNO Q
# Platform: Qualcomm Dragonwing QRB2210 (ARM64, 4 GB RAM, 32 GB eMMC)
set -euo pipefail

echo "=========================================================="
echo " SlowSloth — Arduino UNO Q Setup & Deployment"
echo "=========================================================="

# 1. Detect dynamic Linux user and paths
TARGET_USER="$(whoami)"
TARGET_HOME="$HOME"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[INFO] Running as user: ${TARGET_USER}"
echo "[INFO] Home directory:  ${TARGET_HOME}"
echo "[INFO] Application dir: ${APP_DIR}"

# 2. Hardware and Architecture Verification
ARCH="$(uname -m)"
echo "[INFO] System architecture: ${ARCH}"
if [[ "${ARCH}" != "aarch64" && "${ARCH}" != "arm64" ]]; then
    echo "[WARNING] Target is not ARM64 (${ARCH}). SlowSloth will run in cross-platform development mode."
fi

# Detect OS Release
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    echo "[INFO] Detected OS: ${PRETTY_NAME:-$ID}"
fi

# Audit RAM
if command -v free >/dev/null 2>&1; then
    TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
    AVAIL_RAM_MB=$(free -m | awk '/^Mem:/{print $7}')
    echo "[INFO] Total RAM: ${TOTAL_RAM_MB} MB | Available RAM: ${AVAIL_RAM_MB} MB"
    if [[ ${TOTAL_RAM_MB} -lt 3500 ]]; then
        echo "[WARNING] Board RAM is under 4 GB. Ensure background processes are minimized."
    fi
fi

# Audit Storage
if command -v df >/dev/null 2>&1; then
    DISK_AVAIL=$(df -h "${APP_DIR}" | awk 'NR==2 {print $4}')
    echo "[INFO] Available storage on data partition: ${DISK_AVAIL}"
fi

# 3. System package dependencies
echo ""
echo "[1/4] Checking system package prerequisites..."
if command -v apt-get >/dev/null 2>&1; then
    echo "[INFO] Updating package lists and installing Python 3 + SQLite..."
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-venv python3-pip sqlite3
fi

# 4. Virtual Environment Setup
echo ""
echo "[2/4] Initializing Python virtual environment..."
VENV_DIR="${APP_DIR}/venv"
if [[ ! -d "${VENV_DIR}" ]]; then
    python3 -m venv "${VENV_DIR}"
    echo "[INFO] Virtual environment created at ${VENV_DIR}"
fi

echo "[INFO] Installing Python dependencies..."
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"

# 5. Local Data Directory Setup
mkdir -p "${APP_DIR}/data"
chmod 755 "${APP_DIR}/data"

# 6. AI Inference Runtime Choice & Confirmation
echo ""
echo "[3/4] AI Inference Configuration"
echo "SlowSloth defaults to the deterministic rule-based parser ('dev_mock') with zero cloud dependencies."
echo "llama.cpp with Gemma 2 2B GGUF is the approved candidate for local inference on Arduino UNO Q."
echo ""
read -p "Would you like to install/configure llama.cpp and download Gemma 2 2B (Q4_K_M ~1.6 GB)? [y/N]: " -r INSTALL_MODEL || INSTALL_MODEL="n"

if [[ "${INSTALL_MODEL}" =~ ^[Yy]$ ]]; then
    echo "[INFO] Preparing llama.cpp and Gemma 2 2B..."
    # Model download instructions / guarded pull
    mkdir -p "${APP_DIR}/models"
    echo "[NOTE] Place gemma-2-2b-it-Q4_K_M.gguf into ${APP_DIR}/models/"
else
    echo "[INFO] Retaining verified 'dev_mock' deterministic parser. No models downloaded."
fi

# 7. Generate systemd Service Unit
echo ""
echo "[4/4] Generating systemd service unit..."
SERVICE_FILE="/tmp/slowsloth.service"
cat <<EOF > "${SERVICE_FILE}"
[Unit]
Description=SlowSloth Edge AI Task Assistant
After=network.target

[Service]
Type=simple
User=${TARGET_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${VENV_DIR}/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=SLOWSLOTH_HOST=127.0.0.1
Environment=SLOWSLOTH_PORT=8000
Environment=SLOWSLOTH_DB_PATH=${APP_DIR}/data/slowsloth.db
Environment=SLOWSLOTH_TIMEZONE=Asia/Kolkata

[Install]
WantedBy=multi-user.target
EOF

echo "[INFO] Systemd service generated at ${SERVICE_FILE}"
echo "To install the service permanently on Arduino UNO Q, run:"
echo "  sudo cp ${SERVICE_FILE} /etc/systemd/system/slowsloth.service"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable --now slowsloth.service"
echo ""
echo "=========================================================="
echo " Setup complete! SlowSloth is ready on Arduino UNO Q."
echo " Start manually with: ${VENV_DIR}/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000"
echo "=========================================================="
