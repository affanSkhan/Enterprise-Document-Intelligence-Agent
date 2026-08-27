export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const TENANT_KEY = "ei.tenant";
export const TOKEN_KEY = "ei.token";

export type Session = { access_token: string; token_type: string; expires_in: number };
export type Document = { id: string; filename: string; file_type: string; created_at: string; updated_at?: string; status: string; current_version?: number };
export type Job = { job_id: string; document_id: string; status: string; checkpoint: string; attempts: number; max_attempts: number; error?: string | null };
export type Evidence = { id: string; content: string; metadata?: { filename?: string; chunk_id?: string; doc_id?: string; chunk_idx?: number; version?: number }; trust?: string; retrieval_score?: number };
export type ChatResponse = { answer: string; evidence: Evidence[]; verified: boolean; confidence: number; abstained: boolean; model: string | null; retrieval: { mode: string; reranked: boolean; candidate_count: number; accepted_evidence: number; acl_enforced: boolean } };

export function getToken() { return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY); }
export function getTenant() { return typeof window === "undefined" ? "" : window.localStorage.getItem(TENANT_KEY) || ""; }
export function saveSession(tenant: string, session: Session) { window.localStorage.setItem(TOKEN_KEY, session.access_token); window.localStorage.setItem(TENANT_KEY, tenant); }
export function clearSession() { window.localStorage.removeItem(TOKEN_KEY); window.localStorage.removeItem(TENANT_KEY); }

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers, cache: "no-store" });
  const body = await res.text();
  let data: unknown = null;
  try { data = body ? JSON.parse(body) : null; } catch { data = body; }
  if (!res.ok) {
    const detail = typeof data === "object" && data && "detail" in data ? String((data as {detail?: unknown}).detail) : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return data as T;
}

export async function login(tenant: string, email: string, password: string) {
  const form = new URLSearchParams();
  form.set("username", email); form.set("password", password); form.set("tenant_id", tenant);
  const res = await fetch(`${API_BASE}/api/auth/token`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: form, cache: "no-store" });
  const data = await res.json() as Session & { detail?: string };
  if (!res.ok) throw new Error(data.detail || "Invalid credentials");
  saveSession(tenant, data); return data;
}

export const api = {
  health: () => request<{status:string}>('/api/health'),
  documents: () => request<Document[]>('/api/documents'),
  upload: async (file: File) => { const form = new FormData(); form.append('file', file); return request<{document_id:string;job_id:string;status:string;checkpoint:string;queued:boolean}>('/api/documents/upload', {method:'POST', body:form}); },
  job: (id: string) => request<Job>(`/api/jobs/${id}`),
  search: (query: string, top_k = 5) => request<{results: Evidence[]}>('/api/search', {method:'POST', body:JSON.stringify({query,top_k,mode:'hybrid',rerank:true})}),
  chat: (query: string, top_k = 6) => request<ChatResponse>('/api/chat', {method:'POST', body:JSON.stringify({query,top_k})}),
  report: (topic: string) => request<{result:string}>('/api/agents/report', {method:'POST', body:JSON.stringify({topic})}),
  presentation: (topic: string) => request<{result:Array<{title:string;bullet_points:string[]}>|object}>('/api/agents/presentation', {method:'POST', body:JSON.stringify({topic})}),
};
