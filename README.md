# SlowSloth 🦥

> **Think Less About Tasks. Let Your Sloth Handle the Sorting.**

SlowSloth is a local-first, privacy-respecting AI personal task assistant engineered specifically for edge computing on the **Arduino UNO Q** (Qualcomm Dragonwing QRB2210, 4 GB RAM, 32 GB eMMC, ARM64 Linux) and local development workstations. 

It accepts free-form, unstructured thoughts (reminders, quick ideas, project tasks), processes them on-device, and organizes them into structured, actionable tasks with suggested priorities, explicit deadlines, action steps, and daily briefings—stored safely in a local SQLite database with **zero cloud dependencies**.

---

## Key Features

- **Local-First & Offline**: Zero telemetry or third-party AI APIs (no OpenAI, no Gemini, no external network calls at runtime). Everything stays on your board.
- **Thought to Actionable Tasks**: Ingests messy thoughts like:
  > *"Need to finish the README for my AI project, check the battery model results, and email my mentor tomorrow. I should probably do the results first."*
  And structures them into prioritized tasks with concrete next action steps.
- **Strict Grounding & No Date Hallucinations**: Relative expressions (e.g., *"tomorrow"*, *"next Monday"*) are resolved using your configured local timezone (`Asia/Kolkata` by default). Tasks without explicit temporal mentions are strictly left without deadlines.
- **Review Before Saving**: Extracted suggestions are presented in a review dialog allowing you to adjust titles, deadlines, or priorities before confirming them to the database.
- **Grounded Daily Briefings**: Synthesizes an on-demand daily executive summary strictly grounded in database records (overdue tasks, due today, high-priority inbox).
- **Persistent SQLite Storage**: Survives board restarts, browser reloads, and power cycles with safe schema migrations and parameterized queries.
- **Lightweight Vanilla Web UI**: Built using pure HTML5, CSS3, and Vanilla JavaScript ES Modules in a dark navy theme (`#0B132B`) with cyan accents (`#00B4D8`) and an original SVG sloth mascot. No React or Node.js build pipeline required!
- **Edge-Safe Memory Budget**: Designed to operate safely within the 4 GB RAM boundary of the Arduino UNO Q.

---

## Hardware Target & Architecture

```
Browser Dashboard (Vanilla HTML5 / CSS3 / ES Modules)
          |
          | HTTP Requests (127.0.0.1:8000)
          v
FastAPI Backend (Async Python)
  ├── Security & LAN Guard Middleware
  ├── Date Parser Engine (Asia/Kolkata Aware)
  ├── Task Management Service
  ├── Daily Briefing Generator (Database-Grounded)
  ├── AI Extraction Service
  │     ├── [Active] Deterministic Rule-Based Engine (DEV MOCK ENGINE)
  │     └── [Edge Candidate] llama.cpp / llama-server (Gemma 2 2B GGUF)
  └── SQLite Database (data/slowsloth.db with auto-migrations)
```

### Arduino UNO Q Hardware Profile:
- **MPU**: Qualcomm Dragonwing™ QRB2210 (Quad-core Arm® Cortex®-A53 up to 2.0 GHz) + Adreno™ 702 GPU.
- **MCU**: STMicroelectronics STM32U585 running Zephyr OS. *(SlowSloth runs purely on the Linux MPU side; no sensors or peripherals needed).*
- **RAM**: 4 GB LPDDR4.
- **Storage**: 32 GB eMMC.
- **OS**: ARM64 Linux (Debian variant).

### 4 GB RAM Allocation (Projected):
- **Debian Linux OS**: ~500 MB
- **SlowSloth Backend**: ~120 MB
- **Gemma 2 2B Q4_K_M GGUF**: ~1,600 MB (1.6 GB)
- **KV Cache (2048 Context) + Buffers**: ~480 MB
- **Estimated Peak RAM**: **~2,700 MB (~2.7 GB)**
- **Safety Headroom**: **~1,396 MB (~1.4 GB)**

---

## Quick Start (Local Development on Windows / Linux / macOS)

### 1. Prerequisites
- Python 3.10+
- SQLite 3

### 2. Setup
Clone the repository:
```bash
git clone https://github.com/your-username/SlowSloth.git
cd SlowSloth
```

Create a virtual environment and install dependencies:
```bash
# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Launch Development Server
```bash
# Windows
scripts\run_dev.bat

# Linux / macOS
chmod +x scripts/run_dev.sh
./scripts/run_dev.sh
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## Deployment on Arduino UNO Q (Debian 13 ARM64)

### 1. Run Automated Setup Script
On the Arduino UNO Q board:
```bash
chmod +x scripts/setup_uno_q.sh
./scripts/setup_uno_q.sh
```
The script dynamically detects the board's user (e.g. `arduino` or `uno`), checks available RAM and storage, installs system dependencies, configures the virtual environment, and generates a systemd service.

### 2. Enable Persistent Service on Boot
```bash
sudo cp /tmp/slowsloth.service /etc/systemd/system/slowsloth.service
sudo systemctl daemon-reload
sudo systemctl enable --now slowsloth.service
```

---

## AI Runtime & Qualcomm Compatibility Analysis

1. **Qualcomm AI Hub Investigation**:
   - Qualcomm AI Hub hosts pre-compiled generative AI models optimized for Qualcomm's high-tier Hexagon Tensor Processors (Snapdragon 8 Gen 2/3, Snapdragon X Elite, QCS6490/QCS8550).
   - The **Qualcomm QRB2210** on the Arduino UNO Q is an entry-tier SoC with Cortex-A53 cores and an Adreno 702 GPU; it **lacks the high-end Hexagon NPU** required by AI Hub's pre-compiled LLM bundles.
2. **Approved Edge AI Candidate**:
   - **`llama.cpp`** compiled for ARM64 Linux running quantized **Gemma 2 2B Q4_K_M** (or Gemma 2B Q4_0).
3. **Deterministic Dev Mock Mode**:
   - SlowSloth is currently pre-configured with a transparent, deterministic rule-based parser (`DEV MOCK ENGINE`).
   - The dashboard and status endpoints clearly identify this mode and will never falsely claim that local model inference occurred until a live open-weight model is verified.

---

## Verification & Automated Test Suite

Run the full automated test suite:
```bash
python -m pytest tests/ -v
```

### Verified Test Results (Windows Development Workstation):
```
tests/test_ai_extraction.py::test_deterministic_mock_extraction PASSED   [  3%]
tests/test_ai_extraction.py::test_extraction_is_deterministic PASSED     [  7%]
tests/test_ai_extraction.py::test_fallback_when_runtime_missing PASSED   [ 10%]
tests/test_ai_extraction.py::test_error_raised_if_fallback_disabled PASSED [ 14%]
tests/test_briefing.py::test_empty_briefing PASSED                       [ 17%]
tests/test_briefing.py::test_grounded_briefing_with_tasks PASSED         [ 21%]
tests/test_database.py::test_migration_idempotency PASSED                [ 25%]
tests/test_database.py::test_data_persistence_across_connections PASSED  [ 28%]
tests/test_database.py::test_foreign_key_on_delete_set_null PASSED       [ 32%]
tests/test_date_parser.py::test_no_deadline_found PASSED                 [ 35%]
tests/test_date_parser.py::test_tomorrow_parsing PASSED                  [ 39%]
tests/test_date_parser.py::test_today_and_tonight_parsing PASSED         [ 42%]
tests/test_date_parser.py::test_day_after_tomorrow PASSED                [ 46%]
tests/test_date_parser.py::test_in_n_days PASSED                         [ 50%]
tests/test_date_parser.py::test_month_boundary_rollover PASSED           [ 53%]
tests/test_date_parser.py::test_year_boundary_rollover PASSED            [ 57%]
tests/test_date_parser.py::test_midnight_transition PASSED               [ 60%]
tests/test_security_xss.py::test_sql_injection_safety PASSED             [ 64%]
tests/test_security_xss.py::test_xss_payload_preservation PASSED         [ 67%]
tests/test_security_xss.py::test_lan_access_guard PASSED                 [ 71%]
tests/test_task_crud.py::test_task_create_and_read PASSED                [ 75%]
tests/test_task_crud.py::test_task_update PASSED                         [ 78%]
tests/test_task_crud.py::test_task_complete_and_reopen PASSED            [ 82%]
tests/test_task_crud.py::test_task_deletion PASSED                       [ 85%]
tests/test_task_crud.py::test_view_filters PASSED                        [ 89%]
tests/test_task_crud.py::test_search_filter PASSED                       [ 92%]
tests/test_thought_confirmation.py::test_organize_and_confirm_workflow PASSED [ 96%]
tests/test_thought_confirmation.py::test_confirm_nonexistent_thought PASSED [100%]

============================= 28 passed in 5.80s ==============================
```

---

## Security & LAN Access

- **Localhost Binding**: SlowSloth binds to `127.0.0.1` by default to prevent unauthorized network exposure.
- **LAN Access Protection**: If `ENABLE_LAN_ACCESS=true` is enabled in `.env` for local network access:
  - Configure `LAN_API_KEY=your_secret_key`.
  - Callers over the LAN must provide the `X-SlowSloth-Key` HTTP header. Unauthenticated network requests are rejected with `401 Unauthorized` or `403 Forbidden`.
- **SQL Injection Prevention**: All database queries use parameterized SQL via `aiosqlite`.
- **XSS Prevention**: All user-provided fields (task titles, notes, categories) are strictly rendered using DOM `textContent` APIs.

---

## Model Licences vs. Software Licence

- **Software Code Licence**: MIT License (see [LICENSE](file:///D:/Downloads/SlowSloth/LICENSE)).
- **Model Licences**: Any AI model weights downloaded for use with SlowSloth (such as Google's Gemma models) are governed separately under their respective terms (e.g., [Google Gemma Terms of Use](https://ai.google.dev/gemma/terms)). The MIT software license does **not** grant or modify permissions for model weights.

---

## Demonstration Script

Try entering this sample input in the quick capture box:
```text
I need to finish the README for my AI project, check the battery model results, and email my mentor tomorrow. I should probably do the results first.
```

Click **Organize Thought**. SlowSloth will extract:
1. **Check the battery model results**: Suggested priority: High | Category: Project | Next Step: Review evaluation metrics and record findings.
2. **Finish the README for my AI project**: Suggested priority: Medium | Category: Project | Next Step: Review installation instructions and documentation.
3. **Email my mentor**: Suggested priority: Medium | Deadline: Tomorrow (resolved to `Asia/Kolkata`) | Category: Communication | Next Step: Draft the email and review it before sending.
