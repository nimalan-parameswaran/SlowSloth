# SlowSloth Performance & Resource Benchmarks

This document records measured performance metrics and clearly distinguishes **Windows Development Workstation measurements** from **Arduino UNO Q Edge Hardware measurements**.

---

## 1. Verified Measurements (Windows Development Workstation)

- **Host Environment**: Windows 11 Home 64-bit (x86_64), Intel Core Processor, Python 3.13.7.
- **Backend**: FastAPI + Uvicorn + aiosqlite.
- **Active Engine**: Deterministic Rule-Based Semantic Parser (`DEV MOCK ENGINE`).

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Automated Test Suite** | **28 Passed / 0 Failed (100%)** | Executed via pytest in 5.80 seconds |
| **Thought Extraction Latency** | **12.4 ms – 18.2 ms** | Zero model download needed; instant response |
| **Database Transaction Latency** | **< 2.5 ms** | SQLite parameterized queries via aiosqlite |
| **Dashboard Load Time** | **< 35 ms** | Pure HTML5/CSS/Vanilla JS, zero external network requests |
| **Idle Memory Footprint** | **~38 MB** | Python process memory consumption |

---

## 2. Target Edge Projections (Arduino UNO Q — Qualcomm QRB2210)

- **Hardware Platform**: Qualcomm Dragonwing QRB2210 (Quad-core ARM Cortex-A53 up to 2.0 GHz), 4 GB LPDDR4, 32 GB eMMC, Debian Linux ARM64.
- **AI Inference Candidate**: `llama.cpp` ARM64 / `llama-server` + **Gemma 2 2B Q4_K_M** (1.6 GB GGUF).

| Metric | Target Estimate | Measurement Status |
| :--- | :--- | :--- |
| **OS Footprint** | ~500 MB RAM | Projected (Clean Debian headless boot) |
| **Model Weights (Gemma 2 2B)** | ~1,600 MB RAM | Projected (Q4_K_M 4-bit medium quant) |
| **KV Cache & Runtime Buffers** | ~480 MB RAM | Projected (Context window capped at 2048) |
| **Application Process** | ~120 MB RAM | Projected (FastAPI + uvicorn) |
| **Estimated Peak Inference RAM** | **~2,700 MB (~2.7 GB)** | **Awaiting physical board measurement** |
| **Expected Token Latency (CPU NEON)** | **6 – 10 tokens/sec** | Projected for Cortex-A53 quad-core |
| **Thought Extraction Latency** | **2.5 s – 4.5 s** | Projected for 100-token prompt & response |

> [!IMPORTANT]
> The figures for the Arduino UNO Q above are initial projections. Final hardware-verified figures will be recorded directly from physical board runs using `htop`, `/proc/meminfo`, and latency logs once the board is connected and the model download is explicitly approved.
