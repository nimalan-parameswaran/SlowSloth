/**
 * Main application controller for SlowSloth Multi-Agent Assistant.
 */

import { api } from "./api.js";
import { showToast, formatDateTime, formatTimeRange, openModal, closeModal, escapeHtml } from "./ui.js";

const state = {
  currentSection: "overview",
  currentTaskView: "all",
  currentTaskPriority: "",
  taskSearchQuery: "",
  pendingBundle: null,
};

document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

async function initApp() {
  setupNavigation();
  setupEventListeners();
  await loadSystemStatus();
  await refreshActiveSection();
}

// 1. Navigation Shell Controller
function setupNavigation() {
  const navButtons = document.querySelectorAll(".nav-item");
  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      navButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const sectionName = btn.dataset.section;
      switchSection(sectionName);
    });
  });

  const topCaptureBtn = document.getElementById("quick-capture-top-btn");
  if (topCaptureBtn) {
    topCaptureBtn.addEventListener("click", () => {
      document.querySelector('[data-section="capture"]').click();
      document.getElementById("plan-thought-input").focus();
    });
  }
}

function switchSection(name) {
  state.currentSection = name;
  document.querySelectorAll(".app-section").forEach((sec) => sec.classList.remove("active"));
  const target = document.getElementById(`section-${name}`);
  if (target) target.classList.add("active");

  const titles = {
    overview: { title: "Overview", subtitle: "Your personal daily command center" },
    capture: { title: "Capture / Inbox", subtitle: "Multi-agent intent analysis and action proposal" },
    tasks: { title: "Tasks", subtitle: "Organize, prioritize, and track execution" },
    calendar: { title: "Calendar", subtitle: "Agenda schedule and meeting coordination" },
    reminders: { title: "Reminders", subtitle: "Scheduled notifications and alerts" },
    briefing: { title: "Daily Briefing", subtitle: "Grounded morning briefing and priority summary" },
    activity: { title: "Agent Activity", subtitle: "Transparent audit log of autonomous operations" },
    settings: { title: "Settings", subtitle: "Integrations, timezones, and AI engine status" },
  };

  const info = titles[name] || { title: "SlowSloth", subtitle: "" };
  document.getElementById("page-title").textContent = info.title;
  document.getElementById("page-subtitle").textContent = info.subtitle;

  refreshActiveSection();
}

async function refreshActiveSection() {
  if (state.currentSection === "overview") loadOverview();
  else if (state.currentSection === "tasks") loadTasks();
  else if (state.currentSection === "calendar") loadCalendar();
  else if (state.currentSection === "reminders") loadReminders();
  else if (state.currentSection === "briefing") loadBriefing();
  else if (state.currentSection === "activity") loadActivity();
  else if (state.currentSection === "settings") loadSettings();
}

// 2. Event Listeners Setup
function setupEventListeners() {
  // Capture Form (Planner Agent)
  const planForm = document.getElementById("plan-form");
  const planInput = document.getElementById("plan-thought-input");
  const charCounter = document.getElementById("char-counter");

  planInput.addEventListener("input", () => {
    charCounter.textContent = `${planInput.value.length} / 4000`;
  });

  planForm.addEventListener("submit", handlePlanThought);

  // Review Screen Actions
  document.getElementById("approve-bundle-btn").addEventListener("click", handleApproveBundle);
  document.getElementById("discard-bundle-btn").addEventListener("click", () => {
    state.pendingBundle = null;
    document.getElementById("review-panel").style.display = "none";
  });

  // Task Filter Tabs
  document.querySelectorAll(".view-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".view-tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.currentTaskView = btn.dataset.view;
      loadTasks();
    });
  });

  // Task Priority & Search
  document.getElementById("priority-filter").addEventListener("change", (e) => {
    state.currentTaskPriority = e.target.value;
    loadTasks();
  });

  let searchTimeout;
  document.getElementById("task-search-input").addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.taskSearchQuery = e.target.value;
      loadTasks();
    }, 250);
  });

  // Calendar Event Modal
  document.getElementById("create-event-btn").addEventListener("click", () => {
    openModal("create-event-modal");
  });

  document.getElementById("create-event-form").addEventListener("submit", handleCreateEvent);

  // Reminders Check
  document.getElementById("process-due-reminders-btn").addEventListener("click", async () => {
    try {
      const res = await api.request("/api/reminders/process-due", { method: "POST" });
      showToast(`Processed: ${res.delivered} delivered, ${res.missed} missed.`);
      loadReminders();
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // Refresh Briefing
  document.getElementById("refresh-briefing-btn").addEventListener("click", loadBriefing);

  // Google OAuth Form
  document.getElementById("google-config-form").addEventListener("submit", handleConnectGoogle);
  document.getElementById("google-disconnect-btn").addEventListener("click", handleDisconnectGoogle);

  // Modal Closers
  document.querySelectorAll(".modal-close-btn, .modal-cancel-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const modal = e.target.closest(".modal-overlay");
      if (modal) modal.classList.remove("active");
    });
  });
}

// 3. Section Renderers

// --- OVERVIEW ---
async function loadOverview() {
  try {
    const [tasks, events, reminders] = await Promise.all([
      api.getTasks(),
      api.getCalendarEvents(),
      api.getReminders({ status: "scheduled" }),
    ]);

    const activeTasks = tasks.filter((t) => !t.is_completed);
    const overdueTasks = tasks.filter((t) => !t.is_completed && t.deadline && new Date(t.deadline) < new Date());

    document.getElementById("stat-tasks-count").textContent = activeTasks.length;
    document.getElementById("stat-events-count").textContent = events.length;
    document.getElementById("stat-reminders-count").textContent = reminders.length;
    document.getElementById("stat-overdue-count").textContent = overdueTasks.length;

    // Render Today's tasks preview
    const todayTasksContainer = document.getElementById("overview-today-tasks");
    todayTasksContainer.innerHTML = "";
    if (activeTasks.length === 0) {
      todayTasksContainer.innerHTML = "<p style='color: var(--ink-mute); font-size: 0.88rem;'>No active tasks.</p>";
    } else {
      activeTasks.slice(0, 3).forEach((t) => {
        const item = document.createElement("div");
        item.style.cssText = "display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--hairline);";
        item.innerHTML = `
          <span style="font-size: 0.9rem; font-weight: 500;">${escapeHtml(t.title)}</span>
          <span class="pill-badge prio-${t.priority}">${t.priority}</span>
        `;
        todayTasksContainer.appendChild(item);
      });
    }

    // Render Upcoming events preview
    const upcomingEventsContainer = document.getElementById("overview-upcoming-events");
    upcomingEventsContainer.innerHTML = "";
    if (events.length === 0) {
      upcomingEventsContainer.innerHTML = "<p style='color: var(--ink-mute); font-size: 0.88rem;'>No scheduled meetings.</p>";
    } else {
      events.slice(0, 3).forEach((e) => {
        const item = document.createElement("div");
        item.style.cssText = "display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--hairline);";
        item.innerHTML = `
          <span style="font-size: 0.9rem; font-weight: 500;">${escapeHtml(e.title)}</span>
          <span class="num-tabular" style="font-size: 0.82rem; color: var(--primary);">${formatTimeRange(e.start_time, e.end_time)}</span>
        `;
        upcomingEventsContainer.appendChild(item);
      });
    }
  } catch (err) {
    console.error("Failed to load overview:", err);
  }
}

// --- CAPTURE / PLANNER AGENT ---
async function handlePlanThought(e) {
  e.preventDefault();
  const input = document.getElementById("plan-thought-input");
  const btn = document.getElementById("plan-btn");
  const text = input.value.trim();

  if (text.length < 3) {
    showToast("Please enter at least 3 characters.", "error");
    return;
  }

  btn.disabled = true;
  btn.textContent = "Analyzing Intent...";

  try {
    const bundle = await api.planThought(text);
    state.pendingBundle = bundle;
    renderReviewBundle(bundle);
  } catch (err) {
    showToast(`Planning failed: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Understand & Plan";
  }
}

function renderReviewBundle(bundle) {
  const panel = document.getElementById("review-panel");
  panel.style.display = "block";
  panel.scrollIntoView({ behavior: "smooth" });

  document.getElementById("planner-notes").textContent = bundle.planner_notes;

  // Ambiguities
  const ambBox = document.getElementById("ambiguities-alert");
  if (bundle.ambiguities && bundle.ambiguities.length > 0) {
    ambBox.style.display = "block";
    ambBox.textContent = "⚠️ Clarifications: " + bundle.ambiguities.join(" | ");
  } else {
    ambBox.style.display = "none";
  }

  // Events
  document.getElementById("review-events-count").textContent = bundle.events.length;
  const eventsList = document.getElementById("review-events-list");
  eventsList.innerHTML = "";
  if (bundle.events.length === 0) {
    eventsList.innerHTML = "<p style='color: var(--ink-mute); font-size: 0.85rem;'>None detected.</p>";
  } else {
    bundle.events.forEach((evt, idx) => {
      const row = document.createElement("div");
      row.className = "action-item-row";
      row.innerHTML = `
        <div class="action-item-header">
          <input type="text" class="input-text rev-evt-title" data-idx="${idx}" value="${escapeHtml(evt.title)}" />
          <span class="num-tabular" style="font-size: 0.82rem; color: var(--primary); font-weight: 600;">${evt.duration_minutes} min</span>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
          <input type="text" class="input-text rev-evt-start" data-idx="${idx}" value="${evt.start_time}" placeholder="Start (ISO)" />
          <input type="text" class="input-text rev-evt-end" data-idx="${idx}" value="${evt.end_time}" placeholder="End (ISO)" />
        </div>
      `;
      eventsList.appendChild(row);
    });
  }

  // Reminders
  document.getElementById("review-reminders-count").textContent = bundle.reminders.length;
  const remindersList = document.getElementById("review-reminders-list");
  remindersList.innerHTML = "";
  if (bundle.reminders.length === 0) {
    remindersList.innerHTML = "<p style='color: var(--ink-mute); font-size: 0.85rem;'>None detected.</p>";
  } else {
    bundle.reminders.forEach((rem, idx) => {
      const row = document.createElement("div");
      row.className = "action-item-row";
      row.innerHTML = `
        <div class="action-item-header">
          <input type="text" class="input-text rev-rem-title" data-idx="${idx}" value="${escapeHtml(rem.title)}" />
          <span class="pill-badge status-scheduled">Scheduled</span>
        </div>
        <input type="text" class="input-text rev-rem-time" data-idx="${idx}" value="${rem.scheduled_time}" placeholder="Scheduled Time (ISO)" />
      `;
      remindersList.appendChild(row);
    });
  }

  // Tasks
  document.getElementById("review-tasks-count").textContent = bundle.tasks.length;
  const tasksList = document.getElementById("review-tasks-list");
  tasksList.innerHTML = "";
  if (bundle.tasks.length === 0) {
    tasksList.innerHTML = "<p style='color: var(--ink-mute); font-size: 0.85rem;'>None detected.</p>";
  } else {
    bundle.tasks.forEach((t, idx) => {
      const row = document.createElement("div");
      row.className = "action-item-row";
      row.innerHTML = `
        <div class="action-item-header">
          <input type="text" class="input-text rev-task-title" data-idx="${idx}" value="${escapeHtml(t.title)}" />
          <select class="select-box rev-task-prio" data-idx="${idx}" style="width: 100px;">
            <option value="low" ${t.priority === "low" ? "selected" : ""}>Low</option>
            <option value="medium" ${t.priority === "medium" ? "selected" : ""}>Medium</option>
            <option value="high" ${t.priority === "high" ? "selected" : ""}>High</option>
          </select>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
          <input type="text" class="input-text rev-task-deadline" data-idx="${idx}" value="${t.deadline || ""}" placeholder="Deadline (ISO or empty)" />
          <input type="text" class="input-text rev-task-step" data-idx="${idx}" value="${escapeHtml(t.suggested_next_step || "")}" placeholder="Suggested next step" />
        </div>
      `;
      tasksList.appendChild(row);
    });
  }
}

async function handleApproveBundle() {
  if (!state.pendingBundle) return;
  const btn = document.getElementById("approve-bundle-btn");
  btn.disabled = true;
  btn.textContent = "Executing...";

  // Read back any edits from review inputs
  const editedBundle = {
    thought_id: state.pendingBundle.thought_id,
    tasks: [],
    events: [],
    reminders: [],
  };

  document.querySelectorAll(".rev-evt-title").forEach((input, i) => {
    const orig = state.pendingBundle.events[i];
    editedBundle.events.push({
      ...orig,
      title: input.value.trim(),
      start_time: document.querySelectorAll(".rev-evt-start")[i].value.trim(),
      end_time: document.querySelectorAll(".rev-evt-end")[i].value.trim(),
    });
  });

  document.querySelectorAll(".rev-rem-title").forEach((input, i) => {
    const orig = state.pendingBundle.reminders[i];
    editedBundle.reminders.push({
      ...orig,
      title: input.value.trim(),
      scheduled_time: document.querySelectorAll(".rev-rem-time")[i].value.trim(),
    });
  });

  document.querySelectorAll(".rev-task-title").forEach((input, i) => {
    const orig = state.pendingBundle.tasks[i];
    editedBundle.tasks.push({
      ...orig,
      title: input.value.trim(),
      priority: document.querySelectorAll(".rev-task-prio")[i].value,
      deadline: document.querySelectorAll(".rev-task-deadline")[i].value.trim() || null,
      suggested_next_step: document.querySelectorAll(".rev-task-step")[i].value.trim() || null,
      deadline_confirmed: true,
    });
  });

  try {
    const result = await api.executeBundle(editedBundle);
    showToast(`Executed: ${result.created_tasks.length} tasks, ${result.created_events.length} events, ${result.created_reminders.length} reminders.`);
    document.getElementById("plan-thought-input").value = "";
    document.getElementById("review-panel").style.display = "none";
    state.pendingBundle = null;
    switchSection("overview");
  } catch (err) {
    showToast(`Execution failed: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Approve & Execute All";
  }
}

// --- TASKS ---
async function loadTasks() {
  const container = document.getElementById("task-list");
  container.innerHTML = "<p style='color: var(--ink-mute); font-size: 0.88rem;'>Loading tasks...</p>";

  try {
    const tasks = await api.getTasks({
      view: state.currentTaskView,
      priority: state.currentTaskPriority,
      search: state.taskSearchQuery,
    });

    container.innerHTML = "";
    if (tasks.length === 0) {
      container.innerHTML = "<div class='card' style='text-align: center; color: var(--ink-mute);'>No tasks match the selected view.</div>";
      return;
    }

    tasks.forEach((task) => {
      const card = document.createElement("div");
      card.className = `task-card ${task.is_completed ? "completed" : ""}`;
      card.innerHTML = `
        <input type="checkbox" class="task-checkbox" ${task.is_completed ? "checked" : ""} aria-label="Mark completed" />
        <div class="task-content">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="pill-badge prio-${task.priority}">${task.priority}</span>
            <span class="pill-badge category">${escapeHtml(task.category)}</span>
            ${task.deadline ? `<span class="num-tabular" style="font-size: 0.78rem; color: var(--ink-mute);">📅 ${formatDateTime(task.deadline)}</span>` : ""}
          </div>
          <h4 class="task-title">${escapeHtml(task.title)}</h4>
          ${task.description ? `<p class="task-desc">${escapeHtml(task.description)}</p>` : ""}
          ${task.suggested_next_step ? `<div class="task-step">Next Step: ${escapeHtml(task.suggested_next_step)}</div>` : ""}
        </div>
        <button class="btn-pill-danger btn-delete-task" style="align-self: center;">Delete</button>
      `;

      card.querySelector(".task-checkbox").addEventListener("change", async () => {
        await api.toggleComplete(task.id);
        loadTasks();
      });

      card.querySelector(".btn-delete-task").addEventListener("click", async () => {
        if (confirm(`Delete task "${task.title}"?`)) {
          await api.deleteTask(task.id);
          loadTasks();
        }
      });

      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = `<p style='color: var(--ruby);'>Failed to load tasks: ${err.message}</p>`;
  }
}

// --- CALENDAR ---
async function loadCalendar() {
  const container = document.getElementById("calendar-agenda-container");
  container.innerHTML = "<p style='color: var(--ink-mute); font-size: 0.88rem;'>Loading agenda...</p>";

  try {
    const events = await api.getCalendarEvents();
    container.innerHTML = "";
    if (events.length === 0) {
      container.innerHTML = "<div class='card' style='text-align: center; color: var(--ink-mute);'>No calendar events scheduled.</div>";
      return;
    }

    // Group by Date
    const grouped = {};
    events.forEach((evt) => {
      const dt = new Date(evt.start_time).toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
      if (!grouped[dt]) grouped[dt] = [];
      grouped[dt].push(evt);
    });

    Object.keys(grouped).forEach((dateKey) => {
      const dayGroup = document.createElement("div");
      dayGroup.className = "agenda-day-group";
      dayGroup.innerHTML = `<div class="agenda-date-header">${dateKey}</div>`;

      grouped[dateKey].forEach((e) => {
        const card = document.createElement("div");
        card.className = "event-card";
        card.innerHTML = `
          <div>
            <h4 style="font-size: 0.98rem; font-weight: 600; color: var(--ink);">${escapeHtml(e.title)}</h4>
            ${e.description ? `<p style="font-size: 0.82rem; color: var(--ink-mute);">${escapeHtml(e.description)}</p>` : ""}
          </div>
          <div style="display: flex; align-items: center; gap: 14px;">
            <span class="event-time num-tabular">${formatTimeRange(e.start_time, e.end_time)}</span>
            <button class="btn-pill-danger btn-del-event">Cancel</button>
          </div>
        `;
        card.querySelector(".btn-del-event").addEventListener("click", async () => {
          if (confirm(`Cancel event "${e.title}"?`)) {
            await api.deleteCalendarEvent(e.id);
            loadCalendar();
          }
        });
        dayGroup.appendChild(card);
      });

      container.appendChild(dayGroup);
    });
  } catch (err) {
    container.innerHTML = `<p style='color: var(--ruby);'>Failed to load calendar: ${err.message}</p>`;
  }
}

async function handleCreateEvent(e) {
  e.preventDefault();
  const title = document.getElementById("evt-title").value.trim();
  const description = document.getElementById("evt-desc").value.trim() || null;
  const start_time = document.getElementById("evt-start").value.trim();
  const end_time = document.getElementById("evt-end").value.trim();

  try {
    await api.createCalendarEvent({ title, description, start_time, end_time });
    showToast("Event created successfully.");
    closeModal("create-event-modal");
    document.getElementById("create-event-form").reset();
    loadCalendar();
  } catch (err) {
    showToast(`Failed to create event: ${err.message}`, "error");
  }
}

// --- REMINDERS ---
async function loadReminders() {
  const tbody = document.getElementById("reminders-table-body");
  tbody.innerHTML = "<tr><td colspan='6' style='color: var(--ink-mute);'>Loading reminders...</td></tr>";

  try {
    const reminders = await api.getReminders();
    tbody.innerHTML = "";
    if (reminders.length === 0) {
      tbody.innerHTML = "<tr><td colspan='6' style='color: var(--ink-mute); text-align: center;'>No reminders scheduled.</td></tr>";
      return;
    }

    reminders.forEach((r) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-weight: 500; color: var(--ink);">${escapeHtml(r.title)}</td>
        <td class="num-tabular">${formatDateTime(r.scheduled_time)}</td>
        <td class="num-tabular">${r.offset_minutes ? `${r.offset_minutes}m before` : "Exact"}</td>
        <td><span class="pill-badge category">${r.delivery_method}</span></td>
        <td><span class="pill-badge status-${r.status}">${r.status}</span></td>
        <td>
          ${r.status === "delivered" ? `<button class="btn-pill-secondary btn-ack-rem">Acknowledge</button>` : ""}
          <button class="btn-pill-danger btn-del-rem">Cancel</button>
        </td>
      `;

      if (r.status === "delivered") {
        tr.querySelector(".btn-ack-rem").addEventListener("click", async () => {
          await api.acknowledgeReminder(r.id);
          loadReminders();
        });
      }

      tr.querySelector(".btn-del-rem").addEventListener("click", async () => {
        if (confirm(`Cancel reminder "${r.title}"?`)) {
          await api.deleteReminder(r.id);
          loadReminders();
        }
      });

      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan='6' style='color: var(--ruby);'>Failed to load reminders: ${err.message}</td></tr>`;
  }
}

// --- DAILY BRIEFING ---
async function loadBriefing() {
  const summaryEl = document.getElementById("briefing-summary");
  const gridEl = document.getElementById("briefing-sections-grid");
  summaryEl.textContent = "Synthesizing briefing from database...";
  gridEl.innerHTML = "";

  try {
    const briefing = await api.getBriefing();
    summaryEl.textContent = briefing.summary;

    const sections = [
      { label: "Overdue Tasks", count: briefing.sections.overdue.count, color: "var(--ruby)" },
      { label: "Tasks Due Today", count: briefing.sections.today.count, color: "var(--amber)" },
      { label: "Upcoming (3 days)", count: briefing.sections.upcoming.count, color: "var(--primary)" },
      { label: "High Priority Inbox", count: briefing.sections.high_priority_inbox.count, color: "var(--ink-secondary)" },
    ];

    sections.forEach((sec) => {
      const card = document.createElement("div");
      card.className = "stat-metric-card";
      card.innerHTML = `
        <span class="stat-metric-label">${sec.label}</span>
        <span class="stat-metric-value num-tabular" style="color: ${sec.color};">${sec.count}</span>
      `;
      gridEl.appendChild(card);
    });
  } catch (err) {
    summaryEl.textContent = `Could not generate briefing: ${err.message}`;
  }
}

// --- AGENT ACTIVITY ---
async function loadActivity() {
  const tbody = document.getElementById("activity-table-body");
  tbody.innerHTML = "<tr><td colspan='6' style='color: var(--ink-mute);'>Loading activity...</td></tr>";

  try {
    const logs = await api.getAgentActivity(50);
    tbody.innerHTML = "";
    if (logs.length === 0) {
      tbody.innerHTML = "<tr><td colspan='6' style='color: var(--ink-mute); text-align: center;'>No recorded activity yet.</td></tr>";
      return;
    }

    logs.forEach((log) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="num-tabular" style="font-size: 0.8rem; color: var(--ink-mute);">${formatDateTime(log.created_at)}</td>
        <td><span class="pill-badge category" style="font-weight: 600;">${log.agent_name}</span></td>
        <td style="font-size: 0.82rem; color: var(--ink);">${log.action_type}</td>
        <td style="font-size: 0.85rem;">${escapeHtml(log.summary)}</td>
        <td><span class="pill-badge status-${log.status === "success" ? "delivered" : "missed"}">${log.status}</span></td>
        <td class="num-tabular" style="font-size: 0.82rem;">${log.latency_ms ? `${log.latency_ms} ms` : "—"}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan='6' style='color: var(--ruby);'>Failed to load activity: ${err.message}</td></tr>`;
  }
}

// --- SETTINGS & GOOGLE INTEGRATION ---
async function loadSettings() {
  try {
    const status = await api.getGoogleStatus();
    const statusPill = document.getElementById("google-status-pill");
    const connectedBox = document.getElementById("google-connected-box");
    const configForm = document.getElementById("google-config-form");

    if (status.is_connected) {
      statusPill.textContent = "Connected";
      statusPill.className = "pill-badge status-delivered";
      connectedBox.style.display = "block";
      configForm.style.display = "none";
      document.getElementById("google-connected-email").textContent = status.email || "Active Google Account";
    } else {
      statusPill.textContent = "Local Only / Disconnected";
      statusPill.className = "pill-badge category";
      connectedBox.style.display = "none";
      configForm.style.display = "flex";
    }
  } catch (err) {
    console.error("Failed to load settings:", err);
  }
}

async function handleConnectGoogle(e) {
  e.preventDefault();
  const clientId = document.getElementById("google-client-id").value.trim();
  const clientSecret = document.getElementById("google-client-secret").value.trim();

  if (!clientId || !clientSecret) {
    showToast("Please enter both Client ID and Client Secret.", "error");
    return;
  }

  try {
    const res = await api.generateGoogleAuthUrl(clientId, clientSecret);
    showToast("Opening Google OAuth consent screen in a new window...");
    window.open(res.auth_url, "_blank", "width=600,height=700");
  } catch (err) {
    showToast(`OAuth initialization failed: ${err.message}`, "error");
  }
}

async function handleDisconnectGoogle() {
  if (confirm("Disconnect Google Calendar? Scheduled events and local tasks will remain safe.")) {
    try {
      await api.disconnectGoogle();
      showToast("Google Calendar disconnected.");
      loadSettings();
    } catch (err) {
      showToast(`Disconnect failed: ${err.message}`, "error");
    }
  }
}

// --- SYSTEM AUDIT STATUS ---
async function loadSystemStatus() {
  try {
    const status = await api.getSystemStatus();
    const badge = document.getElementById("status-badge");
    const label = document.getElementById("status-label");

    if (status.real_inference_verified) {
      badge.className = "engine-badge ready";
      label.textContent = `Local Gemma 2B Ready`;
    } else {
      badge.className = "engine-badge mock";
      label.textContent = `DEV MOCK ENGINE (Rule-Based)`;
    }

    const tzInput = document.getElementById("setting-tz");
    if (tzInput) tzInput.value = status.timezone;

    const aiInput = document.getElementById("setting-ai-backend");
    if (aiInput) aiInput.value = `${status.active_backend} (${status.model_identifier})`;
  } catch (err) {
    console.error("Failed to fetch system status:", err);
  }
}
