/**
 * Main application controller for SlowSloth.
 */

import { api } from "./api.js";
import { showToast, formatDate, isOverdue, openModal, closeModal } from "./ui.js";

const state = {
  currentView: "all",
  currentPriority: "",
  currentCategory: "all",
  searchQuery: "",
  pendingExtraction: null,
  editingTaskId: null,
};

document.addEventListener("DOMContentLoaded", () => {
  init();
});

async function init() {
  setupEventListeners();
  await loadSystemStatus();
  await loadTasks();
}

function setupEventListeners() {
  // Capture Form
  const captureForm = document.getElementById("capture-form");
  const thoughtInput = document.getElementById("thought-input");
  const charCounter = document.getElementById("char-counter");

  thoughtInput.addEventListener("input", () => {
    charCounter.textContent = `${thoughtInput.value.length} / 4000`;
  });

  captureForm.addEventListener("submit", handleOrganizeThought);

  // Tabs
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.currentView = btn.dataset.view;
      loadTasks();
    });
  });

  // Filter controls
  const priorityFilter = document.getElementById("priority-filter");
  priorityFilter.addEventListener("change", () => {
    state.currentPriority = priorityFilter.value;
    loadTasks();
  });

  const searchInput = document.getElementById("search-input");
  let searchDebounce;
  searchInput.addEventListener("input", () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      state.searchQuery = searchInput.value;
      loadTasks();
    }, 250);
  });

  // Briefing toggle & refresh
  const briefingToggle = document.getElementById("briefing-toggle");
  briefingToggle.addEventListener("click", () => {
    const content = document.getElementById("briefing-content");
    const isHidden = content.style.display === "none";
    content.style.display = isHidden ? "block" : "none";
    if (isHidden) {
      loadBriefing();
    }
  });

  document.getElementById("refresh-briefing-btn").addEventListener("click", (e) => {
    e.stopPropagation();
    loadBriefing();
  });

  // Modals close buttons
  document.querySelectorAll(".modal-close, .modal-cancel").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const modal = e.target.closest(".modal-overlay");
      if (modal) modal.classList.remove("active");
    });
  });

  // Review Modal Confirm
  document.getElementById("confirm-extracted-btn").addEventListener("click", handleConfirmTasks);

  // Edit Task Modal Save
  document.getElementById("save-edit-btn").addEventListener("click", handleSaveEdit);

  // System Status Click
  document.getElementById("status-badge").addEventListener("click", () => {
    openModal("system-modal");
  });
}

async function loadSystemStatus() {
  try {
    const status = await api.getSystemStatus();
    const badge = document.getElementById("status-badge");
    const label = document.getElementById("status-label");

    if (status.real_inference_verified) {
      badge.className = "status-badge ready";
      label.textContent = `Local Gemma 2B Ready (${status.architecture})`;
    } else {
      badge.className = "status-badge mock";
      label.textContent = `DEV MOCK ENGINE (Rule-Based)`;
    }

    // Populate system modal
    document.getElementById("sys-os").textContent = status.platform_os;
    document.getElementById("sys-arch").textContent = status.architecture;
    document.getElementById("sys-python").textContent = status.python_version;
    document.getElementById("sys-backend").textContent = status.active_backend;
    document.getElementById("sys-model").textContent = status.model_identifier;
    document.getElementById("sys-verified").textContent = status.real_inference_verified ? "Yes (Local)" : "No (Deterministic Fallback)";
    document.getElementById("sys-ram").textContent = status.total_ram_mb ? `${status.free_ram_mb} MB free / ${status.total_ram_mb} MB total` : "N/A";
    document.getElementById("sys-disk").textContent = status.disk_free_gb ? `${status.disk_free_gb} GB free` : "N/A";
    document.getElementById("sys-tz").textContent = status.timezone;
  } catch (err) {
    console.error("Failed to fetch system status:", err);
  }
}

async function loadTasks() {
  const container = document.getElementById("task-list");
  container.innerHTML = "<div class='empty-state'><p>Loading tasks...</p></div>";

  try {
    const tasks = await api.getTasks({
      view: state.currentView,
      priority: state.currentPriority,
      category: state.currentCategory,
      search: state.searchQuery,
    });
    renderTasks(tasks);
  } catch (err) {
    container.innerHTML = `<div class='empty-state'><p style='color: var(--priority-high);'>Failed to load tasks: ${err.message}</p></div>`;
  }
}

function renderTasks(tasks) {
  const container = document.getElementById("task-list");
  container.innerHTML = "";

  if (!tasks || tasks.length === 0) {
    const emptyDiv = document.createElement("div");
    emptyDiv.className = "empty-state";
    const h4 = document.createElement("h4");
    h4.textContent = "No tasks found";
    const p = document.createElement("p");
    p.textContent = "Capture a thought above or change your current view/filters.";
    emptyDiv.appendChild(h4);
    emptyDiv.appendChild(p);
    container.appendChild(emptyDiv);
    return;
  }

  tasks.forEach((task) => {
    const card = document.createElement("div");
    card.className = `task-card priority-${task.priority} ${task.is_completed ? "completed" : ""}`;

    // Checkbox container
    const checkContainer = document.createElement("div");
    checkContainer.className = "task-checkbox-container";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "task-checkbox";
    checkbox.checked = task.is_completed;
    checkbox.setAttribute("aria-label", `Mark ${task.title} as complete`);
    checkbox.addEventListener("change", () => handleToggleComplete(task.id));
    checkContainer.appendChild(checkbox);

    // Body
    const body = document.createElement("div");
    body.className = "task-body";

    // Meta top
    const metaTop = document.createElement("div");
    metaTop.className = "task-meta-top";

    const prioBadge = document.createElement("span");
    prioBadge.className = `badge priority-${task.priority}`;
    prioBadge.textContent = task.priority;
    metaTop.appendChild(prioBadge);

    if (task.category) {
      const catBadge = document.createElement("span");
      catBadge.className = "badge category";
      catBadge.textContent = task.category;
      metaTop.appendChild(catBadge);
    }

    body.appendChild(metaTop);

    // Title
    const title = document.createElement("h4");
    title.className = "task-title";
    title.textContent = task.title;
    body.appendChild(title);

    // Description if present
    if (task.description) {
      const desc = document.createElement("p");
      desc.className = "task-desc";
      desc.textContent = task.description;
      body.appendChild(desc);
    }

    // Suggested Next Step
    if (task.suggested_next_step) {
      const step = document.createElement("div");
      step.className = "task-next-step";
      step.textContent = `Suggested Next Step: ${task.suggested_next_step}`;
      body.appendChild(step);
    }

    // Deadline
    if (task.deadline) {
      const deadlineSpan = document.createElement("div");
      const overdue = !task.is_completed && isOverdue(task.deadline);
      deadlineSpan.className = `task-deadline ${overdue ? "overdue" : ""}`;
      const icon = overdue ? "⚠️ Overdue: " : "📅 Due: ";
      deadlineSpan.textContent = `${icon}${formatDate(task.deadline)}${task.deadline_expression ? ` (${task.deadline_expression})` : ""}`;
      body.appendChild(deadlineSpan);
    }

    // Actions
    const actions = document.createElement("div");
    actions.className = "task-actions";

    const editBtn = document.createElement("button");
    editBtn.className = "btn-action";
    editBtn.textContent = "Edit";
    editBtn.addEventListener("click", () => handleEditTask(task));

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "btn-action delete";
    deleteBtn.textContent = "Delete";
    deleteBtn.addEventListener("click", () => handleDeleteTask(task.id, task.title));

    actions.appendChild(editBtn);
    actions.appendChild(deleteBtn);

    card.appendChild(checkContainer);
    card.appendChild(body);
    card.appendChild(actions);

    container.appendChild(card);
  });
}

async function handleOrganizeThought(e) {
  e.preventDefault();
  const input = document.getElementById("thought-input");
  const submitBtn = document.getElementById("organize-btn");
  const text = input.value.trim();

  if (text.length < 3) {
    showToast("Please enter at least 3 characters.", "error");
    return;
  }

  // Prevent duplicate clicks
  submitBtn.disabled = true;
  submitBtn.textContent = "Organizing...";

  try {
    const response = await api.organizeThought(text);
    state.pendingExtraction = response;
    renderReviewModal(response);
    openModal("review-modal");
  } catch (err) {
    showToast(`Extraction failed: ${err.message}`, "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Organize Thought";
  }
}

function renderReviewModal(data) {
  const container = document.getElementById("extracted-tasks-container");
  container.innerHTML = "";

  const infoP = document.getElementById("review-engine-info");
  infoP.textContent = `Engine: ${data.model_name} (${data.backend}) | Time: ${data.processing_time_ms} ms`;

  data.tasks.forEach((task, idx) => {
    const row = document.createElement("div");
    row.className = "extracted-task-row";

    row.innerHTML = `
      <div class="form-group">
        <label>Task Title</label>
        <input type="text" class="review-title" data-idx="${idx}" value="${escapeHtml(task.title)}" />
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Priority</label>
          <select class="review-priority" data-idx="${idx}">
            <option value="low" ${task.priority === "low" ? "selected" : ""}>Low</option>
            <option value="medium" ${task.priority === "medium" ? "selected" : ""}>Medium</option>
            <option value="high" ${task.priority === "high" ? "selected" : ""}>High</option>
          </select>
        </div>
        <div class="form-group">
          <label>Category</label>
          <input type="text" class="review-category" data-idx="${idx}" value="${escapeHtml(task.category || "general")}" />
        </div>
      </div>
      <div class="form-group">
        <label>Deadline (ISO or empty)</label>
        <input type="text" class="review-deadline" data-idx="${idx}" value="${task.deadline || ""}" placeholder="e.g. 2026-10-27T18:00:00+05:30" />
      </div>
      <div class="form-group">
        <label>Suggested Next Step</label>
        <input type="text" class="review-step" data-idx="${idx}" value="${escapeHtml(task.suggested_next_step || "")}" />
      </div>
    `;

    container.appendChild(row);
  });
}

async function handleConfirmTasks() {
  if (!state.pendingExtraction) return;

  const confirmBtn = document.getElementById("confirm-extracted-btn");
  confirmBtn.disabled = true;
  confirmBtn.textContent = "Saving...";

  const titles = document.querySelectorAll(".review-title");
  const priorities = document.querySelectorAll(".review-priority");
  const categories = document.querySelectorAll(".review-category");
  const deadlines = document.querySelectorAll(".review-deadline");
  const steps = document.querySelectorAll(".review-step");

  const tasksToConfirm = [];

  for (let i = 0; i < titles.length; i++) {
    const original = state.pendingExtraction.tasks[i];
    tasksToConfirm.push({
      title: titles[i].value.trim(),
      description: original.description,
      priority: priorities[i].value,
      category: categories[i].value.trim() || "general",
      deadline: deadlines[i].value.trim() || null,
      deadline_expression: original.deadline_expression,
      deadline_confidence: original.deadline_confidence,
      deadline_confirmed: true,
      suggested_next_step: steps[i].value.trim() || null,
    });
  }

  try {
    await api.confirmTasks(state.pendingExtraction.thought_id, tasksToConfirm);
    showToast(`Successfully confirmed ${tasksToConfirm.length} tasks!`);
    closeModal("review-modal");
    document.getElementById("thought-input").value = "";
    document.getElementById("char-counter").textContent = "0 / 4000";
    state.pendingExtraction = null;
    await loadTasks();
  } catch (err) {
    showToast(`Confirmation failed: ${err.message}`, "error");
  } finally {
    confirmBtn.disabled = false;
    confirmBtn.textContent = "Confirm & Save Tasks";
  }
}

async function handleToggleComplete(taskId) {
  try {
    await api.toggleComplete(taskId);
    await loadTasks();
  } catch (err) {
    showToast(`Failed to update task: ${err.message}`, "error");
  }
}

function handleEditTask(task) {
  state.editingTaskId = task.id;
  document.getElementById("edit-title").value = task.title;
  document.getElementById("edit-description").value = task.description || "";
  document.getElementById("edit-priority").value = task.priority;
  document.getElementById("edit-category").value = task.category || "general";
  document.getElementById("edit-deadline").value = task.deadline || "";
  document.getElementById("edit-step").value = task.suggested_next_step || "";
  openModal("edit-modal");
}

async function handleSaveEdit() {
  if (!state.editingTaskId) return;

  const payload = {
    title: document.getElementById("edit-title").value.trim(),
    description: document.getElementById("edit-description").value.trim() || null,
    priority: document.getElementById("edit-priority").value,
    category: document.getElementById("edit-category").value.trim() || "general",
    deadline: document.getElementById("edit-deadline").value.trim() || null,
    suggested_next_step: document.getElementById("edit-step").value.trim() || null,
  };

  try {
    await api.updateTask(state.editingTaskId, payload);
    showToast("Task updated successfully.");
    closeModal("edit-modal");
    state.editingTaskId = null;
    await loadTasks();
  } catch (err) {
    showToast(`Save failed: ${err.message}`, "error");
  }
}

async function handleDeleteTask(taskId, title) {
  if (confirm(`Are you sure you want to delete "${title}"?`)) {
    try {
      await api.deleteTask(taskId);
      showToast("Task deleted.");
      await loadTasks();
    } catch (err) {
      showToast(`Delete failed: ${err.message}`, "error");
    }
  }
}

async function loadBriefing() {
  const summaryEl = document.getElementById("briefing-summary");
  const statsEl = document.getElementById("briefing-stats");
  summaryEl.textContent = "Generating daily briefing from database...";
  statsEl.innerHTML = "";

  try {
    const briefing = await api.getBriefing();
    summaryEl.textContent = briefing.summary;

    const overdueCount = briefing.sections.overdue.count;
    const todayCount = briefing.sections.today.count;
    const upcomingCount = briefing.sections.upcoming.count;
    const inboxCount = briefing.sections.high_priority_inbox.count;

    statsEl.innerHTML = `
      <span class="stat-chip ${overdueCount > 0 ? "overdue" : ""}">Overdue: ${overdueCount}</span>
      <span class="stat-chip">Due Today: ${todayCount}</span>
      <span class="stat-chip">Upcoming (3 days): ${upcomingCount}</span>
      <span class="stat-chip">High Priority Inbox: ${inboxCount}</span>
    `;
  } catch (err) {
    summaryEl.textContent = `Could not generate briefing: ${err.message}`;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
