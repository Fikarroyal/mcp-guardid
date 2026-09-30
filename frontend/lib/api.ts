const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("mcp_guardid_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user_id: string; role: string; full_name: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, full_name: string, password: string) =>
    request<{ access_token: string; user_id: string; role: string; full_name: string }>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, full_name, password }),
    }),
  me: () => request("/api/v1/auth/me"),

  listUsers: () => request("/api/v1/users"),
  createUser: (body: Record<string, unknown>) => request("/api/v1/users", { method: "POST", body: JSON.stringify(body) }),
  updateUser: (id: string, body: Record<string, unknown>) =>
    request(`/api/v1/users/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteUser: (id: string) => request(`/api/v1/users/${id}`, { method: "DELETE" }),

  listApiKeys: () => request("/api/v1/api-keys"),
  createApiKey: (body: Record<string, unknown>) => request("/api/v1/api-keys", { method: "POST", body: JSON.stringify(body) }),
  revokeApiKey: (id: string) => request(`/api/v1/api-keys/${id}/revoke`, { method: "POST" }),
  deleteApiKey: (id: string) => request(`/api/v1/api-keys/${id}`, { method: "DELETE" }),

  listRoles: () => request("/api/v1/roles"),
  updateRole: (id: string, body: Record<string, unknown>) =>
    request(`/api/v1/roles/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  listPermissions: () => request("/api/v1/roles/permissions"),
  setPermission: (role_name: string, category: string, allowed: boolean) =>
    request(
      `/api/v1/roles/permissions/set?role_name=${encodeURIComponent(role_name)}&category=${category}&allowed=${allowed}`,
      { method: "PUT" }
    ),

  listExecutions: (tool?: string, status?: string) => {
    const qs = new URLSearchParams();
    if (tool) qs.set("tool", tool);
    if (status) qs.set("status_filter", status);
    return request(`/api/v1/executions${qs.toString() ? `?${qs}` : ""}`);
  },
  deleteExecution: (id: string) => request(`/api/v1/executions/${id}`, { method: "DELETE" }),
  purgeExecutions: (days: number) => request(`/api/v1/executions/purge?older_than_days=${days}`, { method: "POST" }),

  createTool: (body: Record<string, unknown>) => request("/api/v1/tools", { method: "POST", body: JSON.stringify(body) }),
  updateTool: (id: string, body: Record<string, unknown>) =>
    request(`/api/v1/tools/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteTool: (id: string) => request(`/api/v1/tools/${id}`, { method: "DELETE" }),

  listTools: () => request("/api/v1/tools"),
  getTool: (id: string) => request(`/api/v1/tools/${id}`),
  searchTools: (query: string, top_k?: number) =>
    request("/api/v1/tools/search", { method: "POST", body: JSON.stringify({ query, top_k }) }),
  executeTool: (id: string, payload: { input_data?: Record<string, unknown>; target?: string; reason?: string }) =>
    request(`/api/v1/tools/${id}/execute`, { method: "POST", body: JSON.stringify(payload) }),

  agentQuery: (query: string, session_id?: string) =>
    request("/api/v1/agent/query", { method: "POST", body: JSON.stringify({ query, session_id }) }),

  listApprovals: (status?: string) =>
    request(`/api/v1/approvals${status ? `?status_filter=${status}` : ""}`),
  approveApproval: (id: string, decision_note?: string) =>
    request(`/api/v1/approvals/${id}/approve`, { method: "POST", body: JSON.stringify({ decision_note }) }),
  rejectApproval: (id: string, decision_note?: string) =>
    request(`/api/v1/approvals/${id}/reject`, { method: "POST", body: JSON.stringify({ decision_note }) }),

  listAudit: (params: Record<string, string | number | undefined> = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined) as [string, string][]
    ).toString();
    return request(`/api/v1/audit${qs ? `?${qs}` : ""}`);
  },

  listIncidents: () => request("/api/v1/incidents"),

  ragSearch: (query: string, category?: string, top_k = 5) =>
    request("/api/v1/rag/search", { method: "POST", body: JSON.stringify({ query, category, top_k }) }),

  runEvaluation: (dataset_name: string, sample_size: number) =>
    request("/api/v1/evaluation/run", { method: "POST", body: JSON.stringify({ dataset_name, sample_size }) }),
  listEvaluationResults: () => request("/api/v1/evaluation/results"),

  listSecurityEvents: (limit = 100) => request(`/api/v1/security/events?limit=${limit}`),

  systemHealth: () => request("/api/v1/system/health"),
};

export function setToken(token: string) {
  if (typeof window !== "undefined") window.localStorage.setItem("mcp_guardid_token", token);
}
export function clearToken() {
  if (typeof window !== "undefined") window.localStorage.removeItem("mcp_guardid_token");
}
export function hasToken(): boolean {
  return !!getToken();
}
