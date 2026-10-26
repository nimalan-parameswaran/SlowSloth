# SlowSloth 🦥

> **Think Less About Tasks. Let Your Sloth Handle the Sorting.**

SlowSloth is a local-first, privacy-respecting **multi-agent personal assistant** engineered for edge computing on the **Arduino UNO Q** (Qualcomm Dragonwing QRB2210, 4 GB RAM, 32 GB eMMC, ARM64 Linux) and local development workstations.

SlowSloth implements the full productivity loop:
$$\text{Capture Thought} \longrightarrow \text{Understand Intent} \longrightarrow \text{Propose Actions} \longrightarrow \text{User Approves} \longrightarrow \text{Execute} \longrightarrow \text{Track} \longrightarrow \text{Remind}$$

Example input:
> *"I have a project meeting tomorrow at 10 AM for 30 minutes. Remind me 15 minutes before, and prepare the presentation today."*

SlowSloth automatically extracts and coordinates:
1. **Meeting**: Tomorrow 10:00 AM – 10:30 AM (`Asia/Kolkata`).
2. **Reminder**: Scheduled for 9:45 AM tomorrow (15 min before meeting).
3. **Task**: "Prepare the presentation" due today.
4. **Structured Review**: Editable pre-execution review dialog where users adjust details or deselect actions before confirming.

---

## Complete Design

SlowSloth features a functional, editorial light design system inspired by Stripe:
- **Palette**: Deep navy ink (`#0d253d`), secondary ink (`#273951`), electric indigo primary (`#533afd`), muted text (`#64748d`), white canvas (`#ffffff`), soft background (`#f6f9fc`), and subtle borders (`#e3e8ee`).
- **Atmospheric Gradient Mesh**: Subtle pastel gradient mesh header banner anchoring the workspace.
- **Pill Buttons & Clean Cards**: Tight-radius pills (`border-radius: 9999px`) and minimal-shadow white cards.
- **Tabular Figures**: Numeric alignment for times, dates, and metric counters (`font-variant-numeric: tabular-nums`).
- **Sidebar Application Shell**: Persistent navigation rail spanning:
  1. **Overview** (Today's metrics, schedule, priority tasks)
  2. **Capture / Inbox** (Thought intake & multi-action proposal review)
  3. **Tasks** (Filter views: Today, Upcoming, Overdue, Inbox, All)
  4. **Calendar** (Local agenda-first view with event creation)
  5. **Reminders** (Scheduled, delivered, missed lifecycle with restart recovery)
  6. **Daily Briefing** (Executive grounded summary from database)
  7. **Agent Activity** (Transparent, privacy-safe audit log)
  8. **Settings** (Timezone, Google Calendar integration, AI engine status)

---

## Multi-Agent Architecture

```
User Thought (Text Input)
          |
          v
Planner / Orchestrator Agent
          |
          +---- Multi-Action Intent Parser (Meetings, Reminders, Tasks, Ambiguities)
          |
          v
Structured Action Proposal (Editable Review Screen)
          |
     [User Approves]
          |
Coordinator Agent (Atomic SQLite Transaction)
  ├── Task Agent ----------> tasks table
  ├── Calendar Agent ------> calendar_events + calendar_sync_queue (Outbox)
  ├── Reminder Agent ------> reminders table (Restart Recovery & Lifecycle)
  └── Activity Logger -----> agent_activity table (Audit Log)
```

### Specialized Agents:
1. **Planner Agent**: Analyzes thoughts, identifies intents (tasks, meetings, reminders), checks date/time ambiguities, and proposes actions without making unapproved mutations.
2. **Task Agent**: Manages task CRUD, deadlines, priorities, categories, and completion states.
3. **Calendar Agent**: Manages local agenda events and handles optional Google Calendar OAuth 2.0 synchronization via an asynchronous outbox queue (`calendar_sync_queue`).
4. **Reminder Agent**: Manages reminder lifecycles (`scheduled`, `due`, `delivered`, `acknowledged`, `missed`, `failed`, `cancelled`), with automated restart recovery for overdue reminders.
5. **Daily Briefing Agent**: Synthesizes an on-demand morning briefing grounded directly in current database tasks and calendar events.

---

## Google Calendar Integration (Optional)

SlowSloth runs **100% offline out-of-the-box** using a local SQLite agenda engine. Google Calendar is an optional integration.

### Setting Up Google Cloud Console:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable the **Google Calendar API**.
3. Configure the **OAuth Consent Screen** (select User Type: External or Internal).
4. Add the scope: `https://www.googleapis.com/auth/calendar.events`.
5. Under **Credentials**, create an **OAuth 2.0 Client ID** (Application type: *Web application*).
6. Set the **Authorized redirect URI** to:
   ```
   http://127.0.0.1:8000/api/integrations/google/callback
   ```
7. Open SlowSloth, navigate to **Settings > Google Calendar Integration**, enter your `Client ID` and `Client Secret`, and click **Connect with Google**.

---

## Quick Start (Local Development)

### 1. Prerequisites
- Python 3.10+
- SQLite 3

### 2. Setup
```bash
git clone https://github.com/your-username/SlowSloth.git
cd SlowSloth

# Create virtual environment and install dependencies
python -m venv venv
venv\Scripts\activate   # On Windows
# source venv/bin/activate  # On Linux / macOS

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

Navigate to: `http://127.0.0.1:8000`

---

## Automated Verification & Test Results

Run the full automated test suite:
```bash
python -m pytest tests/ -v
```

### Verified Test Results (Windows Development Workstation):
```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-8.4.2
rootdir: D:\Downloads\SlowSloth
configfile: pytest.ini
asyncio: mode=Mode.AUTO
collected 40 items

tests/test_ai_extraction.py::test_deterministic_mock_extraction PASSED   [  2%]
tests/test_ai_extraction.py::test_extraction_is_deterministic PASSED     [  5%]
tests/test_ai_extraction.py::test_fallback_when_runtime_missing PASSED   [  7%]
tests/test_ai_extraction.py::test_error_raised_if_fallback_disabled PASSED [ 10%]
tests/test_briefing.py::test_empty_briefing PASSED                       [ 12%]
tests/test_briefing.py::test_grounded_briefing_with_tasks PASSED         [ 15%]
tests/test_calendar_service.py::test_calendar_crud_and_outbox PASSED     [ 17%]
tests/test_database.py::test_migration_idempotency PASSED                [ 20%]
tests/test_database.py::test_data_persistence_across_connections PASSED  [ 22%]
tests/test_database.py::test_foreign_key_on_delete_set_null PASSED       [ 25%]
tests/test_date_parser.py::test_no_deadline_found PASSED                 [ 27%]
tests/test_date_parser.py::test_tomorrow_parsing PASSED                  [ 30%]
tests/test_date_parser.py::test_today_and_tonight_parsing PASSED         [ 32%]
tests/test_date_parser.py::test_day_after_tomorrow PASSED                [ 35%]
tests/test_date_parser.py::test_in_n_days PASSED                         [ 37%]
tests/test_date_parser.py::test_month_boundary_rollover PASSED           [ 40%]
tests/test_date_parser.py::test_year_boundary_rollover PASSED            [ 42%]
tests/test_date_parser.py::test_midnight_transition PASSED               [ 45%]
tests/test_frontend_serving.py::test_frontend_index_serving PASSED       [ 47%]
tests/test_frontend_serving.py::test_static_assets_serving PASSED        [ 50%]
tests/test_integrations.py::test_google_integration_initial_status PASSED [ 52%]
tests/test_integrations.py::test_google_auth_url_generation PASSED       [ 55%]
tests/test_integrations.py::test_google_oauth_callback_invalid_state PASSED [ 57%]
tests/test_integrations.py::test_google_disconnect PASSED                [ 60%]
tests/test_multiagent_orchestration.py::test_multi_action_thought_planning PASSED [ 62%]
tests/test_multiagent_orchestration.py::test_ambiguity_detection PASSED  [ 65%]
tests/test_multiagent_orchestration.py::test_coordinator_execution_and_idempotency PASSED [ 67%]
tests/test_reminder_service.py::test_reminder_lifecycle PASSED           [ 70%]
tests/test_reminder_service.py::test_restart_recovery_and_missed_status PASSED [ 72%]
tests/test_security_xss.py::test_sql_injection_safety PASSED             [ 75%]
tests/test_security_xss.py::test_xss_payload_preservation PASSED         [ 77%]
tests/test_security_xss.py::test_lan_access_guard PASSED                 [ 80%]
tests/test_task_crud.py::test_task_create_and_read PASSED                [ 82%]
tests/test_task_crud.py::test_task_update PASSED                         [ 85%]
tests/test_task_crud.py::test_task_complete_and_reopen PASSED            [ 87%]
tests/test_task_crud.py::test_task_deletion PASSED                       [ 90%]
tests/test_task_crud.py::test_view_filters PASSED                        [ 92%]
tests/test_task_crud.py::test_search_filter PASSED                       [ 95%]
tests/test_thought_confirmation.py::test_organize_and_confirm_workflow PASSED [ 97%]
tests/test_thought_confirmation.py::test_confirm_nonexistent_thought PASSED [100%]

============================= 40 passed in 5.53s ==============================
```

---

## Licences

- **Source Code**: [MIT License](file:///D:/Downloads/SlowSloth/LICENSE).
- **Model Licences**: Local AI model weights (such as Google Gemma) are governed separately under their respective terms (e.g., [Google Gemma Terms of Use](https://ai.google.dev/gemma/terms)).
