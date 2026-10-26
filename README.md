# SlowSloth 🦥
> **Think Less About Tasks. Let Your Sloth Handle the Sorting.**

SlowSloth is a local-first personal AI task-management butler designed for busy students and people juggling multiple commitments. It aims to turn natural-language thoughts into organised tasks, prioritise work, and help schedule it in **Google Calendar**.

Built for the **Arduino UNO Q**, SlowSloth is designed around local AI inference using Google's open-weight Gemma model family, with **Gemma 3 1B** as the selected model for local task interpretation.

The motivation is personal. Between hackathons, research, courses, workshops, competitive exams, social volunteering, and time with family and friends, managing commitments can become a job of its own. SlowSloth aims to reduce that administrative effort so users can spend more time doing their work and less time organising it.

The idea is simple:

**Capture a thought. Let your assistant organise it. Review the plan. Get back to life.**

## At a glance

- **Local AI goal:** Run Gemma 3 1B on the Arduino UNO Q for natural-language task interpretation.
- **AI task assistant:** Turn compound thoughts into structured task proposals.
- **Priority-based planning:** Help decide which tasks deserve attention first.
- **Google Calendar connection:** Designed to synchronise approved scheduling actions with a connected Google Calendar account.
- **Human approval:** Review and edit proposed actions before execution.
- **Local task storage:** SQLite-backed persistence for tasks, events, and reminders.
- **Offline calendar:** Manage local calendar events without requiring Google Calendar connectivity.
- **Reminder management:** Track reminder states and recover from application restarts.
- **Daily briefing:** Summarise saved tasks and calendar information.
- **Lightweight dashboard:** Responsive interface built with HTML, CSS, and JavaScript.
- **Development fallback:** Deterministic rule-based processing when a local language model is unavailable.

**Current limitation:** Local Gemma 3 1B inference and physical deployment on the Arduino UNO Q must be verified on the actual hardware. The existing rule-based development engine is not a language model.

---

## Why SlowSloth?

A busy student can have several competing priorities on the same day: finishing a research experiment, preparing a hackathon submission, attending a workshop, studying for an exam, and remembering a personal commitment.

A conventional task manager still expects the user to enter the details, assign priorities, create calendar events, and maintain reminders.

SlowSloth aims to reduce those manual steps.

Instead of manually converting every thought into individual records, the user can enter a natural-language request such as:

> I need to finish my research report, prepare for tomorrow's exam, and attend a project meeting at 10 AM. The exam preparation should come first. Remind me 15 minutes before the meeting.

The intended workflow is to extract the separate actions, identify their priorities and deadlines, prepare a proposed schedule, and let the user review it before execution.

With Google Calendar connected, approved meeting and scheduling actions can be sent to the user's calendar through the integration.

The goal is not to let an AI make every decision independently. It is to reduce the repetitive work between having an intention and acting on it.

## How it works

**Capture → Interpret → Prioritise → Propose → Review → Confirm → Schedule → Track**

1. **Capture:** Enter a thought containing one or more tasks.
2. **Interpret:** Extract the requested actions and relevant dates or times.
3. **Prioritise:** Determine the relative urgency of tasks using their deadlines, stated preferences, and other available information.
4. **Propose:** Prepare structured task, meeting, and reminder proposals.
5. **Review:** Edit, approve, or reject the proposed actions.
6. **Confirm:** Validate the approved actions before execution.
7. **Schedule:** Save local events and, when connected and authorised, synchronise eligible events with Google Calendar.
8. **Track:** Follow task status, upcoming commitments, and reminders.

Missing deadlines should remain unset unless the user supplies enough information to resolve them. Ambiguous dates should be flagged for review rather than guessed.

Priority-based planning must also respect real calendar availability. A task marked urgent should not automatically displace an existing class, meeting, or personal commitment.

---

## Google Calendar integration

Google Calendar connectivity is an important part of SlowSloth's intended workflow.

A task manager can record what needs to be done, but a calendar helps answer a different question: **When can I actually do it?**

SlowSloth is designed to connect task planning with the user's existing calendar, reducing the need to move information manually between a task list and a scheduling application.

### Intended capabilities

- Connect a Google account using OAuth 2.0.
- Read relevant calendar information, subject to the granted permissions.
- Create approved calendar events from scheduling proposals.
- Associate meetings with reminders and related preparation tasks.
- Use existing calendar commitments when considering available time.
- Queue synchronisation work separately from local database transactions.
- Track synchronisation status and handle eligible retries.
- Continue using the local task manager and offline calendar when Google Calendar is unavailable.

These capabilities describe the intended integration. Automated OAuth flow tests alone do not establish that live account authentication, event creation, synchronisation, and retries have all been verified.

### How the connection is designed

SlowSloth uses a local calendar service and a synchronisation outbox.

The local application stores its own event records. Approved changes intended for Google Calendar can be placed in a synchronisation queue and processed separately by the integration service.

This separation helps keep local task operations independent of temporary network failures. The queue still needs reliable processing, duplicate prevention, error handling, and live API testing before the complete synchronisation workflow can be considered verified.

### Example

Suppose the user enters:

> I have a project meeting tomorrow at 10 AM for 30 minutes. Remind me 15 minutes before, and prepare the presentation today.

SlowSloth is intended to prepare the following proposals:

| Action | Proposed details |
|---|---|
| Meeting | Tomorrow, 10:00–10:30 AM |
| Reminder | 9:45 AM, 15 minutes before the meeting |
| Preparation task | Prepare the presentation, due today |
| Priority | Determined using the user's stated urgency and available task information |

The user reviews the proposals before confirming them. The meeting can then be added to the local calendar and synchronised with Google Calendar when the integration is connected and authorised.

This example assumes the timezone is `Asia/Kolkata` and that the intended dates can be resolved unambiguously.

---

## AI architecture

SlowSloth separates language interpretation, task planning, persistence, calendar operations, and reminder handling.

### Main components

- **Planner / Orchestrator:** Coordinates multi-action planning and the proposed workflow.
- **Intent Parser:** Extracts candidate actions and detects ambiguities.
- **Task Service:** Handles task creation, editing, completion, reopening, and search.
- **Priority Planner:** Helps rank tasks and prepare scheduling proposals using the available task and calendar information.
- **Calendar Service:** Manages local events and prepares eligible changes for external synchronisation.
- **Google Calendar Integration:** Handles authorised communication with Google's Calendar API.
- **Reminder Service:** Tracks reminder states and handles recovery after restarts.
- **Daily Briefing Service:** Summarises information from saved application records.
- **Activity Logger:** Records relevant planning and execution activity.

The coordinator is designed to execute approved action bundles with transactional database operations and idempotency controls.

The distinction between AI interpretation and application execution matters. A model can propose a task or suggest a priority, but application logic must validate the output before it becomes a saved record or an external calendar action.

## Technology stack

| Layer | Technology |
|---|---|
| Target hardware | Arduino UNO Q |
| Target architecture | ARM64 Linux |
| Preferred local model | Gemma 3 1B |
| Potential inference runtime | `llama.cpp`, subject to compatibility testing |
| Backend | FastAPI |
| Data validation | Pydantic |
| Database | SQLite |
| Asynchronous database access | aiosqlite |
| Frontend | HTML, CSS, JavaScript |
| Testing | pytest |
| Calendar integration | Google Calendar API, OAuth 2.0 |
| Development fallback | Deterministic rule-based processing |

The target hardware is reported to include a Qualcomm Dragonwing QRB2210 processor, 4 GB RAM, and 32 GB eMMC. Actual model compatibility, resource consumption, and inference latency need to be measured on the board.

---

## Task management and reminders

### Task dashboard

SlowSloth organises tasks into:

- Today
- Upcoming
- Overdue
- Inbox
- All Tasks

The dashboard also supports task search, filtering, editing, completion, and reopening.

### Local calendar

The offline calendar allows users to manage local events independently of Google Calendar connectivity.

The `calendar_sync_queue` outbox separates local database changes from external synchronisation requests.

### Reminder lifecycle

The reminder service uses explicit states:

`scheduled` → `due` → `delivered` → `acknowledged`

Other states include `missed`, `failed`, and `cancelled`.

Recovery logic handles reminders that become overdue while the application is stopped. The reported implementation marks reminders more than one hour overdue as missed and applies recovery handling to more recent overdue reminders.

Actual notification delivery depends on the configured scheduler and notification mechanism.

### Daily briefing

The Daily Briefing view summarises saved tasks and calendar information, helping users see what needs attention without reviewing every entry individually.

The service is designed to use actual application records instead of inventing tasks or deadlines.

---

## Project status

The following status reflects the reported development state. It should be updated whenever new tests or hardware verification are completed.

| Component | Status |
|---|---|
| Core task-management workflow | Implemented; automated tests reported passing |
| Multi-action planning and review | Implemented; automated tests reported passing |
| Local calendar and outbox services | Implemented; automated tests reported passing |
| Reminder lifecycle and recovery | Implemented; automated tests reported passing |
| Redesigned dashboard | Implemented; frontend serving tests reported passing |
| Google OAuth flow | Automated flow tests reported passing; live account synchronisation not yet verified |
| Rule-based processing | Available for development and testing |
| Gemma 3 1B local inference | Planned; not yet verified |
| Priority-based Google Calendar scheduling | Requires end-to-end verification |
| Physical Arduino UNO Q deployment | Pending hardware verification |

**Reported automated test result:** 40 passed on a Windows 11 development workstation using Python 3.13.7 and pytest 8.4.2.

These workstation results do not establish successful deployment on the Arduino UNO Q or successful live Google Calendar synchronisation.

---

## Quick start: local development

### Prerequisites

- Python 3.10 or later
- Git
- SQLite support

The commands below assume Windows development.

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

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Start the development server

```powershell
.\scripts\run_dev.bat
```

Check the launch script for the configured entry point and options if you need to start the server manually.

Open the dashboard at:

`http://127.0.0.1:8000`

### 5. Run automated tests

```bash
python -m pytest tests/ -v
```

Run the tests against your current checkout before relying on the reported results.

---

## Setting up Google Calendar

To connect Google Calendar, configure a Google Cloud project and OAuth credentials.

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Enable the Google Calendar API.
4. Configure the OAuth consent screen.
5. Create an OAuth 2.0 Client ID for the application.
6. Configure the redirect URI expected by the application.
7. Keep the client secret on the backend.
8. Open SlowSloth's Settings page and follow the Google Calendar connection flow.

The documented development callback is:

`http://127.0.0.1:8000/api/integrations/google/callback`

The integration uses the following Calendar events scope:

`https://www.googleapis.com/auth/calendar.events`

Verify the exact callback URL, scopes, and configuration fields against the current application code before setup.

### Security considerations

- Never expose client secrets or OAuth tokens to browser JavaScript.
- Do not commit credentials to Git.
- Validate OAuth state.
- Request only the required permissions.
- Test authentication and event creation with a separate account before relying on synchronisation.
- Verify duplicate prevention, retries, token handling, and event updates.

Google Calendar connectivity is optional. Local task management and the offline calendar are intended to remain useful without it.

---

## Arduino UNO Q deployment

SlowSloth targets the Arduino UNO Q, with its reported 4 GB RAM and 32 GB eMMC.

The repository includes a proposed deployment script:

`scripts/setup_uno_q.sh`

Inspect the script before running it on the board. Confirm the installation steps, paths, permissions, and service configuration.

The intended verification sequence is:

1. Check available RAM and disk space.
2. Confirm the OS and ARM64 architecture.
3. Transfer the verified project revision.
4. Install dependencies and initialise the database.
5. Run the application using the rule-based engine.
6. Test task creation, review, persistence, calendar operations, and reminder recovery.
7. Test Google Calendar synchronisation with a controlled account.
8. Evaluate Gemma 3 1B with a compatible runtime.
9. Measure inference latency and memory consumption.
10. Verify service startup and recovery after reboot.

**Physical deployment and local Gemma inference remain unverified until tested on the actual board.**

---

## Local AI and open innovation

The objective is to run Gemma 3 1B locally for task interpretation, keeping routine natural-language processing on hardware under the user's control.

A compatible inference runtime such as `llama.cpp` is a candidate, subject to model-format, architecture, and memory testing.

Before deploying the model, verify:

- Model compatibility with the chosen runtime.
- Available RAM and storage.
- Context and inference-buffer requirements.
- Model licensing and usage conditions.
- Inference latency on the actual hardware.
- Correct reporting of the active inference mode.

The current rule-based development engine does not constitute local LLM inference. SlowSloth should identify which engine is active rather than describing fallback results as model-generated output.

Open-weight AI matters here because it allows the model to be run and evaluated under local computing constraints instead of making a hosted inference API mandatory for every task.

Google Calendar is a separate external service. Local model inference does not mean calendar synchronisation is offline: calendar events sent to Google are handled by Google's service under the account's permissions.

---

## Privacy and security

SlowSloth is designed around local task storage and review before action execution.

Its reported implementation includes SQLite persistence, structured data validation, transactional handling of coordinated actions, idempotency controls, OAuth state validation, and selected input-safety tests.

These measures do not guarantee that every deployment is secure by default. Review network binding, authentication, permissions, logs, backups, and secrets before exposing the application beyond local development.

The source code's licence is specified in the repository's `LICENSE` file. Model licences and third-party dependency terms must be reviewed separately.

---

## Contributing

Contributions and practical feedback are welcome.

Useful areas include:

- Natural-language task extraction.
- Priority calculation and scheduling rules.
- Ambiguous date and timezone handling.
- Google Calendar synchronisation and duplicate prevention.
- Reminder delivery and recovery.
- ARM64 memory and inference performance.
- Dashboard accessibility and usability.
- Automated tests and hardware verification.

Please include reproducible test steps and distinguish simulated behaviour from verified external integrations or hardware results.

## Licence

SlowSloth is described as being distributed under the **MIT License**, subject to the terms in the repository's `LICENSE` file. Confirm that the file is present and matches this statement before redistributing the project.

Third-party models, runtimes, and dependencies may have separate licensing conditions.

---

## The idea behind SlowSloth 🦥

> **One thought. A clear plan. Less time managing work.**

SlowSloth is my attempt to reduce the mental overhead of balancing research, hackathons, courses, exams, volunteering, and personal commitments.

By combining local AI task interpretation with priority-based planning and a Google Calendar connection, the goal is to move from a collection of intentions to a schedule that can actually be followed.

The user remains in control of what gets saved and scheduled. The assistant handles the repetitive organisation.

**Less time organising work. More time doing it.** 🦥
