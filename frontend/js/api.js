/**
 * API client module for SlowSloth backend.
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
      errorDetail = await response.text() || errorDetail;
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const api = {
  // Thought organization
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

  // Task CRUD
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

  // Briefing
  getBriefing: () => request("/api/briefing"),

  // System status
  getSystemStatus: () => request("/api/system/status"),
};
