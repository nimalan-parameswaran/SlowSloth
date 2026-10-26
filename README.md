# SlowSloth 🦥

> **Think Less About Tasks. Let Your Sloth Handle the Sorting.**

**SlowSloth** is a local-first personal productivity assistant designed to transform natural-language thoughts into structured, reviewable actions. It combines task management, multi-action planning, a local calendar, reminders, and daily briefings in a lightweight application targeting the **Arduino UNO Q** and local development workstations.

The target platform features the Qualcomm Dragonwing QRB2210, 4 GB RAM, 32 GB eMMC, and ARM64 Linux.

The central idea is simple: capture a thought, review the proposed actions, and let the application handle repetitive organisation while keeping the user in control.

## At a glance

- **Local-first architecture:** SQLite-backed task management and offline calendar functionality.
- **Multi-action planning:** Interpret compound thoughts and prepare structured task, meeting, and reminder proposals.
- **Human approval:** Review and edit proposed actions before execution.
- **Reminder lifecycle:** Track reminder states and handle overdue reminders during recovery.
- **Optional integration:** Google Calendar OAuth 2.0 and an outbox-based synchronisation design.
- **Lightweight interface:** Responsive browser-based dashboard using HTML, CSS, and JavaScript.
- **Development fallback:** Deterministic rule-based processing when a local language model is unavailable.
- **Edge-computing target:** Arduino UNO Q deployment, with hardware-specific compatibility and performance still requiring verification.

## Project status

| Component | Status |
|---|---|
| Core task-management workflow | Implemented; automated tests reported passing |
| Multi-action planning and review | Implemented; automated tests reported passing |
| Local calendar and outbox services | Implemented; automated tests reported passing |
| Reminder lifecycle and recovery | Implemented; automated tests reported passing |
| Redesigned dashboard | Implemented; frontend serving tests reported passing |
| Google OAuth flow | Automated flow tests reported passing; live account synchronisation not yet verified |
| Rule-based processing | Available for development and testing |
| Local Gemma inference | Planned; not yet verified |
| Physical Arduino UNO Q deployment | Pending hardware verification |

**Reported automated test result:** 40 passed on a Windows 11 development workstation using Python 3.13.7 and pytest 8.4.2. See [Automated Testing](#automated-testing).

These results describe the reported workstation test run. They do not establish successful deployment on the Arduino UNO Q or successful live Google Calendar synchronisation.

---

## How it works

SlowSloth is designed around a review-first productivity workflow:

**Capture → Understand → Propose → Review → Confirm → Execute → Track → Remind**

For example, a user enters:

> I have a project meeting tomorrow at 10 AM for 30 minutes. Remind me 15 minutes before, and prepare the presentation today.

The intended workflow produces structured proposals for:

1. **Meeting:** Tomorrow, 10:00–10:30 AM.
2. **Reminder:** 15 minutes before the meeting, at 9:45 AM.
3. **Preparation task:** Prepare the presentation, due today.
4. **Review:** Edit, approve, or deselect proposed actions before confirming them.

The example assumes the user's local timezone is `Asia/Kolkata` and that the date and time can be resolved unambiguously.

SlowSloth is designed to avoid inventing missing deadlines or silently committing ambiguous actions. The user should remain able to review proposed details before execution.

## Features

### 1. Multi-agent productivity workflow

The application separates planning, task management, calendar operations, reminders, and activity logging into specialised services.

- **Planner / Orchestrator:** Coordinates compound thoughts and prepares structured action proposals.
- **Intent Parser:** Splits multi-action input into candidate actions and identifies ambiguities.
- **Task Service:** Manages task creation, updates, completion, reopening, and related task operations.
- **Calendar Service:** Manages local events and prepares changes for optional external synchronisation.
- **Reminder Service:** Tracks reminder states and handles recovery after application restarts.
- **Daily Briefing Service:** Produces a briefing grounded in saved tasks and calendar information.
- **Activity Logger:** Records relevant planning and execution activity for inspection.

The coordinator is designed to execute approved action bundles using SQLite transactions and idempotency controls.

### 2. Task management

The dashboard organises work into views such as:

- Today
- Upcoming
- Overdue
- Inbox
- All Tasks

Additional task-management capabilities include search, filtering, editing, completion, and reopening.

### 3. Local calendar

SlowSloth includes an offline agenda service for creating and managing calendar events locally.

The `calendar_sync_queue` outbox separates local database operations from external API synchronisation. This design helps prevent network latency or temporary connectivity loss from becoming part of the local transaction.

The existence of an outbox does not, by itself, establish that live Google synchronisation has been completed.

### 4. Reminder lifecycle and recovery

The reminder service uses explicit lifecycle states:

`scheduled` → `due` → `delivered` → `acknowledged`

Additional states include:

- `missed`
- `failed`
- `cancelled`

Recovery logic handles reminders that become overdue while the application is stopped. The reported implementation marks reminders more than one hour overdue as missed and applies recovery handling to more recent overdue reminders.

The application also provides an API route for processing due reminders. Actual notification delivery depends on the configured execution and notification mechanisms.

### 5. Daily briefing

The Daily Briefing view summarises saved tasks and calendar information.

The briefing service is designed to use actual application records rather than inventing tasks or deadlines that do not exist in the database.

### 6. Local-first processing

SlowSloth supports a deterministic rule-based development engine. This provides a way to exercise and test task workflows without requiring a language model.

The current reported development configuration uses:

- **Engine:** `DEV MOCK ENGINE`
- **Mode:** `is_mock=True`
- **Cloud AI dependency:** Not required for the deterministic workflow

This is not the same as local LLM inference. The rule-based engine should be identified accurately in the interface and logs.

### 7. Dashboard redesign

The interface uses a light design system inspired by Stripe's visual language.

**Design tokens**

| Element | Value |
|---|---|
| Primary indigo | `#533afd` |
| Deep navy ink | `#0d253d` |
| Secondary ink | `#273951` |
| Muted text | `#64748d` |
| White canvas | `#ffffff` |
| Soft background | `#f6f9fc` |
| Subtle borders | `#e3e8ee` |

The design includes pill-shaped buttons, clean cards, restrained shadows, a subtle gradient-mesh banner, and tabular figures for dates and metrics.

**Eight core views**

1. **Overview** — Summary metrics, today's agenda, and priority tasks.
2. **Capture / Inbox** — Thought intake and multi-action proposal review.
3. **Tasks** — Search, filters, and task management.
4. **Calendar** — Local agenda and event creation.
5. **Reminders** — Reminder status and acknowledgement.
6. **Daily Briefing** — Summary grounded in application records.
7. **Agent Activity** — Inspectable activity log.
8. **Settings** — Timezone, integration configuration, and engine status.

---

## Architecture

```text
                    User Thought
                         |
                         v
               Planner / Orchestrator
                         |
                         v
                  Intent Parser
                         |
                         v
              Structured Action Bundle
                         |
                         v
                 User Review Screen
                         |
                   User Approval
                         |
                         v
                Coordinator Service
                         |
                  SQLite Transaction
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
      Task Service  Calendar Service  Reminder Service
          |              |              |
          v              v              v
        tasks      calendar_events    reminders
                         |
                         v
                 calendar_sync_queue
                         |
                         v
                Optional Google API

             Activity Logger
                    |
                    v
              agent_activity
```

### Technology stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI |
| Data validation | Pydantic |
| Database | SQLite |
| Asynchronous database access | aiosqlite |
| Frontend | HTML, CSS, JavaScript |
| Testing | pytest |
| Target platform | Arduino UNO Q / ARM64 Linux |
| Current fallback engine | Deterministic rule-based processing |
| Potential local inference runtime | `llama.cpp`, subject to compatibility testing |
| Preferred model family | Gemma, subject to model and hardware verification |

---

## Quick start: local development

### Prerequisites

- Python 3.10 or later
- Git
- SQLite support
- A terminal on Windows, Linux, or macOS

The commands below assume you are using Windows for local development.

### 1. Clone the repository

```bash
git clone https://github.com/nimalan-parameswaran/SlowSloth.git
cd SlowSloth
```

### 2. Create a virtual environment

```powershell
python -m venv venv
```

Activate it in PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

If you use Git Bash:

```bash
source venv/Scripts/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the development server

On Windows, use the repository's development launcher:

```powershell
.\scripts\run_dev.bat
```

If you prefer to start the server manually, first check `scripts/run_dev.bat` for the configured application entry point and options.

Open the application at:

**http://127.0.0.1:8000**

Keep the development server running while using the dashboard.

---

## Automated testing

Run the complete test suite from the repository root:

```bash
python -m pytest tests/ -v
```

### Reported test results

The supplied Windows test run reports **40 passed in 5.53 seconds**.

The tests cover:

- Deterministic mock extraction and fallback behaviour
- Daily briefing generation
- Calendar CRUD and outbox operations
- Database migrations and persistence
- Date parsing
- Frontend and static asset serving
- Google integration status and OAuth state validation
- Multi-action planning and ambiguity detection
- Coordinator idempotency
- Reminder lifecycle and restart recovery
- SQL injection and XSS-related handling
- LAN access guard
- Task CRUD, filtering, and search
- Thought review and confirmation

These are the results reported for the Windows development environment. Re-run the test command against your current checkout to verify its present state.

---

## Optional Google Calendar integration

SlowSloth is designed to support offline local calendar use without requiring a Google account. Google Calendar integration is optional.

### Configure Google Cloud

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a Google Cloud project.
3. Enable the Google Calendar API.
4. Configure the OAuth consent screen for the intended account type.
5. Configure the required Calendar events scope:

   `https://www.googleapis.com/auth/calendar.events`

6. Create an OAuth 2.0 Client ID for a web application.
7. Configure the redirect URI expected by the application. The documented development URI is:

   `http://127.0.0.1:8000/api/integrations/google/callback`

8. Open SlowSloth and navigate to **Settings → Google Calendar Integration**.
9. Enter the client credentials through the application's intended configuration flow and connect the Google account.

### Security considerations

- Keep the Google client secret and OAuth tokens on the backend.
- Never expose credentials to browser JavaScript or commit secrets to Git.
- Validate OAuth state to protect against cross-site request forgery.
- Request only the scopes the application needs.
- Verify the complete OAuth and synchronisation workflow with a test account before relying on it.

**Live Google Calendar synchronisation has not been established by the reported automated tests alone.** The actual credential exchange, token handling, event creation, and retry behaviour must be verified separately.

---

## Arduino UNO Q deployment

SlowSloth targets the Arduino UNO Q with the following reported hardware specifications:

- **Processor:** Qualcomm Dragonwing QRB2210
- **Memory:** 4 GB RAM
- **Storage:** 32 GB eMMC
- **Target architecture:** ARM64 Linux

The repository includes a deployment setup script at:

`scripts/setup_uno_q.sh`

The script should be inspected before execution on the board. Confirm its installation steps, paths, permissions, and service configuration first.

### Recommended deployment sequence

1. Check free disk space and available RAM on the board.
2. Confirm the operating system and architecture.
3. Transfer or clone the verified project revision.
4. Install the required Python dependencies.
5. Run database initialisation and application checks.
6. Start SlowSloth in deterministic rule-based mode.
7. Verify dashboard access, task creation, review, persistence, calendar behaviour, and reminder recovery.
8. Check service logs and restart behaviour.
9. Measure idle and active resource consumption.

**Physical Arduino UNO Q deployment remains unverified until these steps are completed on the actual board.**

---

## Local AI: Gemma and `llama.cpp`

The longer-term goal is to run a suitable quantised Gemma model locally, enabling natural-language task interpretation without sending each thought to a hosted inference endpoint.

The candidate configuration is **Gemma 2 2B Instruct, Q4_K_M GGUF**, using a compatible `llama.cpp` runtime.

This remains a planned integration rather than a verified hardware capability.

Before downloading or installing the model:

1. Confirm available storage and memory on the target device.
2. Verify ARM64 runtime compatibility.
3. Confirm the model's terms and redistribution requirements.
4. Evaluate model memory requirements, including context and inference buffers.
5. Benchmark inference latency and memory usage on the actual board.
6. Confirm that the application reports the active inference mode correctly.

A successful workstation test does not guarantee that the same model will run efficiently on the UNO Q.

For model terms, consult the [Google Gemma Terms of Use](https://ai.google.dev/gemma/terms).

---

## Privacy and security

SlowSloth is designed to make local task management possible without a hosted AI service.

Important considerations include:

- Local persistence using SQLite.
- Review before executing proposed action bundles.
- Structured data validation.
- Transactional handling of coordinated actions.
- Idempotency controls to reduce duplicate execution.
- OAuth state validation for the Google integration.
- Backend-only handling of sensitive integration credentials.
- Tests covering selected input-safety and access-control behaviours.

These measures are part of the implementation, not a guarantee that every deployment is secure by default. Review network binding, authentication, permissions, database access, logs, backups, and secrets before exposing the application beyond the local development environment.

For source-code licensing, see [`LICENSE`](LICENSE).

Model licences and terms are separate from the project's source-code licence. Review the applicable model terms before distributing or deploying model weights.

---

## Contributing

Contributions, bug reports, and practical feedback are welcome.

Useful areas to explore include:

- Improving natural-language task extraction.
- Handling ambiguous dates and timezones safely.
- Testing reminder recovery and duplicate prevention.
- Optimising memory usage for ARM64 edge devices.
- Improving accessibility and responsive dashboard behaviour.
- Evaluating compatible local inference runtimes.
- Expanding automated integration and hardware tests.

When submitting changes, include reproducible steps, relevant test results, and a clear distinction between simulated behaviour and verified hardware functionality.

## Licence

SlowSloth's source code is distributed under the **MIT License**, subject to the terms in the repository's [`LICENSE`](LICENSE) file.

Third-party models, runtimes, and dependencies may have their own licences and usage conditions. These must be reviewed separately.

---

## The idea behind SlowSloth 🦥

> **One thought. Structured proposals. Quick review. Actionable tasks.**

SlowSloth explores a practical approach to personal AI: reduce repetitive task administration while keeping the user in control of their data and decisions.

The long-term goal is to make that experience useful on a compact edge device, with local processing, transparent system behaviour, and clear verification of what actually runs on the hardware.

**Less time organising work. More time doing it.**
