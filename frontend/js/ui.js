/**
 * UI helpers and DOM generation with strict XSS sanitization.
 */

export function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

export function formatDate(isoString) {
  if (!isoString) return null;
  try {
    const dt = new Date(isoString);
    if (isNaN(dt.getTime())) return isoString;

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const taskDate = new Date(dt);
    taskDate.setHours(0, 0, 0, 0);

    const diffDays = Math.round((taskDate - today) / (1000 * 60 * 60 * 24));

    const timeStr = dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    if (diffDays === 0) return `Today at ${timeStr}`;
    if (diffDays === 1) return `Tomorrow at ${timeStr}`;
    if (diffDays === -1) return `Yesterday at ${timeStr}`;
    if (diffDays < -1) return `${Math.abs(diffDays)} days overdue`;
    if (diffDays > 1 && diffDays <= 6) {
      const dayName = dt.toLocaleDateString([], { weekday: "short" });
      return `${dayName} at ${timeStr}`;
    }

    return `${dt.toLocaleDateString([], { month: "short", day: "numeric" })} at ${timeStr}`;
  } catch (_) {
    return isoString;
  }
}

export function isOverdue(isoString) {
  if (!isoString) return false;
  try {
    const dt = new Date(isoString);
    return dt < new Date();
  } catch (_) {
    return false;
  }
}

export function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("active");
  }
}

export function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
  }
}
