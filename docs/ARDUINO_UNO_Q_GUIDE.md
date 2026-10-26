# Arduino UNO Q Edge Deployment Guide

This guide details running SlowSloth on the **Arduino UNO Q** single-board computer.

## Hardware Profile: Arduino UNO Q
- **Processor (MPU)**: Qualcomm Dragonwing™ QRB2210 (Quad-core Arm® Cortex®-A53 up to 2.0 GHz) with Adreno™ 702 GPU and Hexagon™ DSP.
- **Microcontroller (MCU)**: STM32U585 running Zephyr OS (for low-level GPIO/real-time tasks).
- **RAM**: 4 GB LPDDR4.
- **Storage**: 32 GB eMMC.
- **Operating System**: Debian Linux (ARM64).

*Note: SlowSloth runs entirely on the Linux MPU side of the UNO Q. No external shields, buttons, or sensor peripherals are required.*

---

## 4 GB RAM Resource Budget (Estimated)

> [!NOTE]
> All figures below are initial engineering estimates and must be verified with physical benchmark tools (`htop`, `/proc/meminfo`) on the physical board.

| Component | RAM (Estimated) | Storage (32 GB eMMC) |
| :--- | :--- | :--- |
| **Debian Linux Minimal OS** | ~500 MB | ~3.5 GB |
| **SlowSloth Python App + SQLite** | ~120 MB | ~150 MB (venv + app) |
| **Gemma 2 2B Q4_K_M GGUF** | ~1,600 MB (1.6 GB) | ~1.7 GB |
| **KV Cache & Context (2048 tokens)** | ~300 MB | N/A |
| **Inference Engine Overhead** | ~180 MB | ~40 MB binary |
| **Estimated Peak Inference RAM** | **~2,700 MB (~2.7 GB)** | **Total Storage Used: ~5.4 GB** |
| **Safety Headroom** | **~1,396 MB (~1.4 GB)** | **Available Storage: > 24 GB** |

---

## Step-by-Step Installation on Arduino UNO Q

### 1. Connect to Arduino UNO Q
Access the board via SSH or the terminal console:
```bash
ssh arduino@<board-ip>
# or ssh uno@<board-ip> depending on your board setup
```

### 2. Clone or Copy SlowSloth Repository
```bash
git clone https://github.com/your-username/SlowSloth.git
cd SlowSloth
```

### 3. Run Automated Setup Script
```bash
chmod +x scripts/setup_uno_q.sh
./scripts/setup_uno_q.sh
```
The script will:
1. Detect your actual Linux username (`whoami`) and home directory.
2. Verify CPU architecture (`aarch64`) and available RAM.
3. Install required system packages (`python3`, `python3-venv`, `sqlite3`).
4. Create the dedicated virtual environment in `venv/`.
5. Install Python dependencies.
6. Generate a tailored systemd service file at `/tmp/slowsloth.service`.

### 4. Enable Background systemd Service
To ensure SlowSloth starts automatically on boot:
```bash
sudo cp /tmp/slowsloth.service /etc/systemd/system/slowsloth.service
sudo systemctl daemon-reload
sudo systemctl enable --now slowsloth.service
```

Check status:
```bash
systemctl status slowsloth.service
```

### 5. Access the Web Dashboard
Open your browser and navigate to:
```
http://127.0.0.1:8000
```
If accessing from a workstation on the local network (LAN):
1. Review security and set `ENABLE_LAN_ACCESS=true` and `LAN_API_KEY=your-secret-key` in `.env`.
2. Bind to `0.0.0.0` or configure reverse proxy.
3. Access `http://<arduino-ip>:8000`.
