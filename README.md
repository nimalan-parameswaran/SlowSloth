# SlowSloth 🦥

> **Think Less About Tasks. Let Your Sloth Handle the Sorting.**

SlowSloth is a local-first personal AI task-management assistant designed for busy students and people juggling multiple commitments. It aims to turn natural-language thoughts into organised tasks, help prioritise work, and schedule approved events through **Google Calendar**.

Built for the **Arduino UNO Q**, SlowSloth is designed to use Google's open-weight Gemma model family, with **Gemma 3 1B** selected for local task interpretation. The project brings together task planning, calendar integration, reminders, and a physical LED-matrix experience.

The motivation is personal. Between hackathons, research, courses, workshops, competitive exams, social volunteering, and time with family and friends, managing commitments can become a job of its own. Recording tasks, assigning priorities, tracking deadlines, and arranging schedules takes time away from the work itself.

SlowSloth aims to reduce that administrative effort.

**Capture a thought. Let your assistant organise it. Review the plan. Get back to life.**

## At a glance

- **Target hardware:** Arduino UNO Q.
- **Local AI goal:** Run Gemma 3 1B for natural-language task interpretation.
- **Task management:** Turn compound thoughts into structured task proposals.
- **Priority-based planning:** Organise work using deadlines, user preferences, and available calendar information.
- **Google Calendar:** Synchronise approved scheduling actions when connected and authorised.
- **Human approval:** Review and edit proposed actions before execution.
- **Local storage:** Persist task information, events, and reminders using SQLite.
- **Local calendar:** Support local event management independently of Google Calendar.
- **Physical reminders:** Use the UNO Q's built-in LED matrix for a sloth face and heartbeat animation.
- **Daily briefing:** Summarise saved tasks and calendar information.
- **Web dashboard:** HTML, CSS, and JavaScript frontend.
- **Development fallback:** Deterministic rule-based processing when a local language model is unavailable.

**Development status:** Core application workflows have reportedly passed automated tests on a Windows development workstation. Local Gemma inference on the UNO Q, live Google Calendar synchronisation, and the complete hardware-integrated reminder workflow still require end-to-end verification.

---

## Why SlowSloth?

Imagine starting your day with a research experiment to finish, an exam to prepare for, a hackathon submission due, a workshop to attend, and a project meeting on your calendar.

The challenge is not always doing the work. Sometimes, it is the repeated effort of organising everything.

A conventional task manager still expects you to enter each task, set priorities, create calendar events, and maintain reminders. When plans change, you have to update everything again.

SlowSloth aims to reduce those steps by letting you express several intentions in natural language and review a structured plan.

For example:

> I need to finish my research report, prepare for tomorrow's exam, and attend a project meeting at 10 AM. Exam preparation should come first.

The intended workflow extracts individual actions, identifies relevant dates and priorities, prepares scheduling proposals, and asks the user to review them before execution.

When Google Calendar is connected, approved calendar actions can be synchronised with the user's account. The UNO Q's LED matrix is designed to provide a physical reminder as an event approaches.

The goal is not to let AI make every decision independently. It is to reduce the repetitive work between having an intention and acting on it.

## How it works

**Capture → Interpret → Prioritise → Propose → Review → Confirm → Schedule → Remind → Track**

1. **Capture:** Enter a thought containing one or more tasks.
2. **Interpret:** Extract candidate actions and relevant dates or times.
3. **Prioritise:** Assess urgency using deadlines, stated preferences, and available information.
4. **Propose:** Prepare structured task, event, and reminder proposals.
5. **Review:** Edit, approve, or reject the proposed actions.
6. **Confirm:** Validate approved actions before execution.
7. **Schedule:** Save local events and synchronise eligible events with Google Calendar when connected and authorised.
8. **Remind:** Track reminder timing and trigger configured notifications or physical LED animations.
9. **Track:** Monitor task status, upcoming commitments, and reminder states.

Missing deadlines should remain unset unless sufficient information is available. Ambiguous dates should be flagged for review instead of guessed.

Priority-based planning should also respect existing calendar commitments. An urgent task should not automatically displace a class, meeting, or personal commitment.

---

## Google Calendar integration

A task manager records what needs to be done. A calendar helps answer a different question:

**When can I actually do it?**

SlowSloth is designed to connect task planning with the user's existing calendar, reducing manual transfers between a task list and a scheduling application.

### Intended capabilities

- Connect a Google account using OAuth 2.0.
- Read calendar information according to the granted permissions.
- Create approved calendar events from scheduling proposals.
- Associate meetings with reminders and related preparation tasks.
- Consider existing calendar commitments when proposing available time.
- Queue synchronisation operations separately from local database transactions.
- Track synchronisation status and handle eligible retries.
- Continue supporting local task management when Google Calendar is unavailable.

These are intended capabilities, not a claim that every integration path has been verified. Automated OAuth flow tests do not, by themselves, prove that live authentication, event creation, updates, and retries work end to end.

### Synchronisation design

SlowSloth maintains local event records and uses a synchronisation outbox named `calendar_sync_queue`.

When a user approves an eligible calendar action, the application can record the local change and queue the external synchronisation operation separately. The integration service can then process queued work without making the local database transaction depend on an immediate Google API response.

Duplicate requests, failures, retries, event updates, and synchronisation status must be handled reliably. These behaviours require integration testing with an authorised Google account.

### Example: from a thought to a calendar event

Suppose the user enters:

> I have a project meeting tomorrow at 10 AM for 30 minutes. Remind me 15 minutes before, and prepare the presentation today.

SlowSloth is intended to prepare the following proposals:

| Action | Proposed details |
|---|---|
| Meeting | Tomorrow, 10:00–10:30 AM |
| Meeting reminder | 9:45 AM |
| Preparation task | Prepare the presentation, due today |
| Priority | Based on stated urgency and available task information |

The user reviews the proposals before confirming them. The meeting can then be saved to the local calendar and synchronised with Google Calendar when the integration is connected and authorised.

This example assumes the timezone is `Asia/Kolkata` and that the intended dates can be resolved unambiguously.

### Google Calendar setup

To configure the integration:

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a Google Cloud project.
3. Enable the Google Calendar API.
4. Configure the OAuth consent screen.
5. Create an OAuth 2.0 Client ID.
6. Configure the redirect URI expected by the application.
7. Store the client secret securely on the backend.
8. Open SlowSloth's Settings page and follow the account-connection flow.

The documented development callback is:

`http://127.0.0.1:8000/api/integrations/google/callback`

The documented Calendar events scope is:

`https://www.googleapis.com/auth/calendar.events`

Verify the current application configuration before using these values.

**Security requirements**

- Keep client secrets and OAuth tokens out of browser JavaScript.
- Never commit credentials to the repository.
- Validate OAuth state.
- Request only the permissions required by the integration.
- Test with a controlled account before relying on calendar synchronisation.
- Verify token handling, duplicate prevention, retries, and event updates.

Google Calendar is optional. Local task management and the local calendar are intended to remain useful without it.

---

## Arduino UNO Q: the physical SlowSloth companion

SlowSloth is designed to do more than organise tasks on a screen. The Arduino UNO Q's built-in **8 × 13 LED matrix** gives the assistant a small physical presence on the desk.

The intended architecture separates responsibilities:

- **Linux side:** Application, task scheduling, persistence, and reminder logic.
- **Microcontroller side:** LED-matrix output and visual animations.

### Sloth face and heartbeat reminder

The LED matrix can display a simple pixel-art sloth face. When a task or calendar event approaches, the display is intended to show a heartbeat animation as a reminder.

The intended behaviour is:

> 10 minutes before a task or event: The sloth face appears, followed by a heartbeat animation.

> One-time alert: The sloth-and-heartbeat sequence runs once for that upcoming task or event. It does not repeatedly blink throughout the remaining ten minutes.

> At the scheduled time: The event follows its scheduled timing; the earlier sloth-and-heartbeat sequence is not repeated.

The goal is to make upcoming commitments noticeable without requiring the user to keep checking a phone or reopening the dashboard.

Because the matrix has only 104 pixels, the animations use simple shapes and visual states rather than detailed illustrations.

**Hardware progress:** The static sloth-face display has been tested on the UNO Q. The heartbeat animation and its timed triggering through the task scheduler must be verified before the complete reminder feature is described as operational.

### Intended reminder flow

1. SlowSloth stores a task or calendar event with a resolved start time.
2. The reminder service calculates the 10-minute-before trigger time.
3. When the reminder becomes due, the Linux application sends the appropriate reminder state to the microcontroller.
4. The LED matrix displays the sloth face followed by the heartbeat animation once.
5. The reminder service records the relevant status and prevents the same reminder from triggering repeatedly.

The Linux application should remain responsible for timing and scheduling. The microcontroller should handle the visual presentation rather than making independent calendar decisions.

The reminder flow must be tested when the browser is closed, the application restarts, the network is unavailable, or a calendar event changes or is cancelled.

---

## AI architecture

SlowSloth separates language interpretation, planning, persistence, calendar operations, and reminder handling.

### Main components

- **Planner / Orchestrator:** Coordinates multi-action planning and the proposed workflow.
- **Intent Parser:** Extracts candidate actions and detects ambiguities.
- **Task Service:** Handles task creation, editing, completion, reopening, and search.
- **Priority Planner:** Helps rank tasks and prepare scheduling proposals.
- **Calendar Service:** Manages local events and prepares eligible changes for synchronisation.
- **Google Calendar Integration:** Handles authorised communication with Google's Calendar API.
- **Reminder Service:** Tracks reminder states and supports recovery after restarts.
- **LED Matrix Controller:** Receives reminder states and controls physical animations.
- **Daily Briefing Service:** Summarises information from saved application records.
- **Activity Logger:** Records relevant planning and execution activity.

The coordinator is designed to execute approved action bundles using transactional database operations and idempotency controls.

AI interpretation and application execution remain separate. A model may propose a task, extract a date, or suggest a priority, but application logic must validate the result before saving it or performing an external action.

### Technology stack

| Layer | Technology |
|---|---|
| Target hardware | Arduino UNO Q |
| Target architecture | ARM64 Linux |
| Selected local model | Gemma 3 1B |
| Candidate inference runtime | `llama.cpp`, subject to compatibility testing |
| Backend | FastAPI |
| Data validation | Pydantic |
| Database | SQLite |
| Asynchronous database access | aiosqlite |
| Frontend | HTML, CSS, JavaScript |
| Automated testing | pytest |
| Calendar integration | Google Calendar API, OAuth 2.0 |
| Hardware display | Built-in LED matrix |
| Development fallback | Deterministic rule-based processing |

The UNO Q is the target for on-device inference. Model compatibility, memory usage, and inference latency must be measured on the actual board before claiming successful deployment.

---

## Task management and reminders

### Task dashboard

SlowSloth organises tasks into:

- Today
- Upcoming
- Overdue
- Inbox
- All Tasks

The dashboard also supports task search, filtering, editing, completion, and reopening, according to the implemented application workflow.

### Local calendar

The local calendar allows users to manage events independently of Google Calendar connectivity.

The `calendar_sync_queue` outbox separates local database changes from external synchronisation requests.

### Reminder lifecycle

The reminder service uses explicit states:

`scheduled` → `due` → `delivered` → `acknowledged`

Other states include `missed`, `failed`, and `cancelled`.

Reported recovery logic marks reminders more than one hour overdue as missed and handles more recent overdue reminders according to the recovery rules.

Actual notification delivery depends on the configured scheduler and notification mechanism. LED-matrix reminders additionally require working communication between the Linux application and the microcontroller.

### Daily briefing

The Daily Briefing view is designed to summarise saved tasks and calendar information, helping users see what needs attention without reviewing every entry individually.

It should use actual application records instead of inventing tasks or deadlines.

---

## Project status

The following table reflects the reported development state. Update it as additional tests are completed.

| Component | Current status |
|---|---|
| Core task-management workflow | Implemented; automated tests reported passing |
| Multi-action planning and review | Implemented; automated tests reported passing |
| Local calendar and outbox services | Implemented; automated tests reported passing |
| Reminder lifecycle and recovery | Implemented; automated tests reported passing |
| Dashboard and frontend serving | Implemented; tests reported passing |
| Google OAuth flow | Automated flow tests reported passing; live account synchronisation not verified |
| Rule-based processing | Available for development and testing |
| Static sloth-face LED display | Tested on the UNO Q |
| Heartbeat LED animation | Requires confirmation of successful hardware testing |
| One-time reminder 10 minutes before an event | End-to-end verification pending |
| Gemma 3 1B local inference | Planned; not yet verified |
| Priority-based Google Calendar scheduling | End-to-end verification pending |
| Full application deployment on UNO Q | Hardware verification pending |

**Reported automated test result:** 40 tests passed on a Windows 11 development workstation using Python 3.13.7 and pytest 8.4.2.

These workstation results do not establish successful deployment on the Arduino UNO Q, live Google Calendar synchronisation, or on-device Gemma inference.

---

## Quick start: local development

### Prerequisites

- Python 3.10 or later, subject to the versions supported by the current dependencies
- Git
- SQLite support

The following commands assume Windows development and that the referenced files exist in the repository.

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

Check the launch script for its configured entry point and options if you need to start the server manually.

Open the dashboard at:

`http://127.0.0.1:8000`

### 5. Run automated tests

```bash
python -m pytest tests/ -v
```

Run the tests against your current checkout before relying on the reported results.

---

## Arduino UNO Q deployment

SlowSloth targets the Arduino UNO Q. Before deploying, verify the board's available memory and storage, operating system, supported model format, inference runtime compatibility, and the project's current Linux setup instructions.

The repository includes a proposed deployment script:

`scripts/setup_uno_q.sh`

Inspect the script before running it. Confirm the installation steps, paths, permissions, and service configuration.

### Recommended verification sequence

1. Check available RAM and disk space.
2. Confirm the operating system and ARM64 architecture.
3. Transfer the verified project revision.
4. Install dependencies and initialise the database.
5. Start the application using the rule-based engine.
6. Test task creation, review, persistence, and local calendar operations.
7. Test reminder timing and recovery after application restarts.
8. Verify communication between the Linux application and the LED-matrix controller.
9. Test Google Calendar authentication and synchronisation with a controlled account.
10. Evaluate Gemma 3 1B using a compatible local inference runtime.
11. Measure inference latency and memory consumption.
12. Verify service startup and recovery after reboot.

Full deployment of the application and local Gemma inference remain unverified until these tests have been completed on the actual board.

---

## Local AI and open innovation

SlowSloth aims to run Gemma 3 1B locally for task interpretation, keeping routine language processing on hardware under the user's control.

A compatible runtime such as `llama.cpp` is a candidate, subject to model-format, architecture, and memory testing.

Before deploying the model, verify:

- Compatibility with the selected inference runtime.
- Available RAM and storage.
- Context and inference-buffer requirements.
- Model licensing and usage conditions.
- Inference latency on the actual hardware.
- That the application correctly identifies whether local inference or the rule-based fallback is active.

The rule-based development engine is not local LLM inference. SlowSloth should not describe fallback results as model-generated output.

Open-weight AI allows developers to evaluate models under local computing constraints instead of making a hosted inference API mandatory for every task.

Google Calendar remains a separate external service. Local model inference does not make calendar synchronisation offline: events sent to Google are handled by Google's service under the account's permissions.

---

## Privacy and security

SlowSloth is designed around local task storage and review before action execution.

The reported implementation includes SQLite persistence, structured data validation, transactional handling of coordinated actions, idempotency controls, OAuth state validation, and selected input-safety tests.

These measures do not guarantee that every deployment is secure by default. Before exposing the application beyond local development, review:

- Network binding and authentication.
- Access controls and filesystem permissions.
- OAuth credentials and token storage.
- Logs and sensitive task information.
- Database backups and recovery.
- External calendar permissions.
- Third-party model and dependency licences.

Local task storage and local inference can reduce dependence on external AI services, but Google Calendar necessarily involves Google's service when synchronisation is enabled.

---

## Contributing

Contributions and practical feedback are welcome.

Useful areas include:

- Natural-language task extraction.
- Priority calculation and scheduling rules.
- Ambiguous date and timezone handling.
- Google Calendar synchronisation and duplicate prevention.
- Reminder delivery and recovery.
- Linux-to-microcontroller communication.
- LED-matrix animations and physical reminder states.
- ARM64 memory use and inference performance.
- Dashboard accessibility and usability.
- Automated tests and hardware verification.

Please include reproducible test steps and distinguish simulated behaviour from verified external integrations or hardware results.

## Licence

Check the repository's `LICENSE` file for the project's actual licence before publishing or redistributing it. Third-party models, runtimes, and dependencies may have separate licensing conditions.

---

## The idea behind SlowSloth 🦥

> **One thought. A clear plan. Less time managing work.**

SlowSloth is my attempt to reduce the mental overhead of balancing research, hackathons, courses, exams, volunteering, and personal commitments.

By combining natural-language task interpretation, priority-based planning, Google Calendar connectivity, and physical LED reminders, the goal is to move from a collection of intentions to a schedule that can actually be followed.

The user remains in control of what gets saved and scheduled. The assistant handles repetitive organisation, while the sloth face and heartbeat animation are designed to provide a physical reminder **once, 10 minutes before a task or event**.

**Less time organising work. More time doing it.** 🦥
