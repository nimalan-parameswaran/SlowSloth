/**
 * API client module for SlowSloth Multi-Agent Assistant.
 */

const BASE_URL = "";

export async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const defaultHeaders = {
    "Content-Type": "application/json",
  };

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    let errorDetail = "An unexpected server error occurred.";
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch (_) {
      errorDetail = (await response.text()) || errorDetail;
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const api = {
  // Planner & Coordinator Agents
  planThought: (text) =>
    request("/api/agents/plan", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  executeBundle: (bundle) =>
    request("/api/agents/execute", {
      method: "POST",
      body: JSON.stringify(bundle),
    }),

  getAgentActivity: (limit = 50) =>
    request(`/api/agents/activity?limit=${limit}`),

  // Calendar
  getCalendarEvents: (params = {}) => {
    const q = new URLSearchParams();
    if (params.start_date) q.append("start_date", params.start_date);
    if (params.end_date) q.append("end_date", params.end_date);
    if (params.status) q.append("status", params.status);
    const qs = q.toString();
    return request(`/api/calendar/events${qs ? `?${qs}` : ""}`);
  },

  createCalendarEvent: (event) =>
    request("/api/calendar/events", {
      method: "POST",
      body: JSON.stringify(event),
    }),

  updateCalendarEvent: (id, updates) =>
    request(`/api/calendar/events/${id}`, {
      method: "PUT",
      body: JSON.stringify(updates),
    }),

  deleteCalendarEvent: (id) =>
    request(`/api/calendar/events/${id}`, {
      method: "DELETE",
    }),

  // Reminders
  getReminders: (params = {}) => {
    const q = new URLSearchParams();
    if (params.status) q.append("status", params.status);
    if (params.delivery_method) q.append("delivery_method", params.delivery_method);
    const qs = q.toString();
    return request(`/api/reminders${qs ? `?${qs}` : ""}`);
  },

  createReminder: (reminder) =>
    request("/api/reminders", {
      method: "POST",
      body: JSON.stringify(reminder),
    }),

  acknowledgeReminder: (id) =>
    request(`/api/reminders/${id}/acknowledge`, {
      method: "PATCH",
    }),

  deleteReminder: (id) =>
    request(`/api/reminders/${id}`, {
      method: "DELETE",
    }),

  // Google Calendar Integration
  getGoogleStatus: () => request("/api/integrations/google/status"),

  generateGoogleAuthUrl: (clientId, clientSecret) =>
    request("/api/integrations/google/auth-url", {
      method: "POST",
      body: JSON.stringify({ client_id: clientId, client_secret: clientSecret }),
    }),

  disconnectGoogle: () =>
    request("/api/integrations/google/disconnect", {
      method: "POST",
    }),

  // Tasks CRUD
  getTasks: (params = {}) => {
    const query = new URLSearchParams();
    if (params.view) query.append("view", params.view);
    if (params.priority) query.append("priority", params.priority);
    if (params.category) query.append("category", params.category);
    if (params.search) query.append("search", params.search);
    const queryString = query.toString();
    return request(`/api/tasks${queryString ? `?${queryString}` : ""}`);
  },

  createTask: (task) =>
    request("/api/tasks", {
      method: "POST",
      body: JSON.stringify(task),
    }),

  updateTask: (id, updates) =>
    request(`/api/tasks/${id}`, {
      method: "PUT",
      body: JSON.stringify(updates),
    }),

  toggleComplete: (id) =>
    request(`/api/tasks/${id}/complete`, {
      method: "PATCH",
    }),

  deleteTask: (id) =>
    request(`/api/tasks/${id}`, {
      method: "DELETE",
    }),

  // Legacy thought organize
  organizeThought: (text) =>
    request("/api/thoughts/organize", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  confirmTasks: (thoughtId, tasks) =>
    request("/api/thoughts/confirm", {
      method: "POST",
      body: JSON.stringify({ thought_id: thoughtId, tasks }),
    }),

  // Briefing
  getBriefing: () => request("/api/briefing"),

  // System
  getSystemStatus: () => request("/api/system/status"),
};
