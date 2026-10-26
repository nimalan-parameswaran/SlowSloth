# SlowSloth Architecture & System Design

SlowSloth is an edge-first, local personal productivity engine designed specifically for resource-constrained platforms like the **Arduino UNO Q** and local workstations.

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
  │     └── [Planned Edge Candidate] llama.cpp / llama-server (Gemma 2 2B GGUF)
  └── SQLite Database (data/slowsloth.db with auto-migrations)
```

## Core Architectural Principles

1. **Local-First & Zero Telemetry**:
   - Zero outbound requests to external cloud AI APIs (no Gemini, OpenAI, or third-party cloud services).
   - Binds strictly to `127.0.0.1` by default.
   - All thoughts, extracted tasks, and edits reside in a local SQLite file (`data/slowsloth.db`).

2. **No Build Pipeline Frontend**:
   - Built with pure HTML5, modern CSS3, and Vanilla JavaScript ES Modules.
   - No npm, Webpack, Vite, or React build step needed. The FastAPI server serves static files directly.
   - Zero external CDNs, fonts, or scripts. Runs 100% offline.

3. **Deterministic Development & Fallback Engine**:
   - During local development or when local LLM runtimes are offline, SlowSloth utilizes a deterministic rule-based semantic parser.
   - The UI and API explicitly display `DEV MOCK ENGINE (Rule-Based)` with `is_mock = True`.
   - Never hallucinates deadlines: relative dates like "tomorrow" are resolved using the local timezone (`Asia/Kolkata`), while tasks without temporal mentions have their deadlines strictly marked as `null` with `deadline_confidence = "unknown"`.

4. **Database Safety & Persistence**:
   - Uses `aiosqlite` with parameterized queries to prevent SQL injection.
   - Migration runner (`backend/database.py`) tracks schema versions in `schema_migrations` and applies schema updates idempotently.
   - Foreign key cascading ensures task associations are maintained without orphaned records.
