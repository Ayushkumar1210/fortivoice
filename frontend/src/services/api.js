const API_BASE_URL = 'http://127.0.0.1:8000';

async function request(endpoint, options = {}, timeoutMs = 20000) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = options.headers || {};

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: options.signal || controller.signal,
      headers,
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMsg = `HTTP Error ${response.status}`;
      try {
        const errJson = await response.json();
        errorMsg = errJson.detail || errJson.message || errorMsg;
      } catch (e) {
        // use fallback message
      }
      throw new Error(errorMsg);
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      console.error(`Request timed out after ${timeoutMs}ms on ${endpoint}`);
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s. Please try again.`);
    }
    console.error(`API Error on ${endpoint}:`, error);
    throw error;
  }
}

export const api = {
  // Analytics
  getDashboardAnalytics: () => request('/api/analytics/dashboard'),

  // Leads
  getLeads: (status = '', search = '') => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (search) params.append('search', search);
    const qs = params.toString();
    return request(`/api/leads${qs ? `?${qs}` : ''}`);
  },
  getLead: (id) => request(`/api/leads/${id}`),
  createLead: (data) => request('/api/leads', { method: 'POST', body: JSON.stringify(data) }),
  updateLead: (id, data) => request(`/api/leads/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteLead: (id) => request(`/api/leads/${id}`, { method: 'DELETE' }),

  // Appointments
  getAppointments: (status = '') => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : '';
    return request(`/api/appointments${qs}`);
  },
  createAppointment: (data) => request('/api/appointments', { method: 'POST', body: JSON.stringify(data) }),
  updateAppointment: (id, data) => request(`/api/appointments/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteAppointment: (id) => request(`/api/appointments/${id}`, { method: 'DELETE' }),

  // Calls
  getCalls: () => request('/api/calls'),
  getCall: (id) => request(`/api/calls/${id}`),
  saveCall: (data) => request('/api/calls', { method: 'POST', body: JSON.stringify(data) }),
  generateCallSummary: (data) => request('/api/calls/summary', { method: 'POST', body: JSON.stringify(data) }),

  // Voice Interaction
  interactVoice: (data) => request('/api/voice/interact', { method: 'POST', body: JSON.stringify(data) }),

  // RAG Knowledge Base
  getDocuments: () => request('/api/rag/documents'),
  uploadDocument: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/api/rag/upload', { method: 'POST', body: formData });
  },
  queryRAG: (query, top_k = 4) => request('/api/rag/query', { method: 'POST', body: JSON.stringify({ query, top_k }) }),
  deleteDocument: (id) => request(`/api/rag/documents/${id}`, { method: 'DELETE' }),

  // Settings
  getSettings: () => request('/api/settings'),
  updateSettings: (data) => request('/api/settings', { method: 'POST', body: JSON.stringify(data) }),
  testGemini: (data = {}) => request('/api/settings/test-gemini', { method: 'POST', body: JSON.stringify(data) }),
  testGroq: (data = {}) => request('/api/settings/test-groq', { method: 'POST', body: JSON.stringify(data) }),
};
