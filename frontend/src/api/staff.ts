export interface StaffSession { access_token: string; staff_id: string; name: string; role: string }
export interface StaffToken { id: string; display_number: string; status: string; serving_started_at: string | null; is_recall: boolean; recall_attempts: number; recall_ready: boolean }
export interface Workstation {
  staff: { id: string; name: string };
  counter: { id: string; label: string; status: string; service_name: string; served_today: number } | null;
  current_token?: StaffToken | null; upcoming?: StaffToken[]; waiting_count?: number; server_time?: string;
  missed?: StaffToken[];
}
export type Action = 'next' | 'start' | 'pause' | 'resume' | 'missed' | 'absent-again';
export interface PendingCommand {
  staff_id: string; counter_id: string; action: Action;
  request_id: string; expected_token_id: string | null; expected_token_status: string | null;
  expected_recall_attempts?: number;
}
export class StaffApiError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}
const base = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');
export async function staffRequest<T>(path: string, session?: StaffSession, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      method: body === undefined ? 'GET' : 'POST', cache: 'no-store', signal: AbortSignal.timeout(15000),
      headers: { ...(session ? { Authorization: `Bearer ${session.access_token}` } : {}),
        ...(body ? { 'Content-Type': body instanceof URLSearchParams ? 'application/x-www-form-urlencoded' : 'application/json' } : {}) },
      body: body === undefined ? undefined : body instanceof URLSearchParams ? body : JSON.stringify(body),
    });
  } catch { throw new StaffApiError(0, 'Connection interrupted. Refresh the counter or retry your saved action.'); }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new StaffApiError(response.status, typeof data.detail === 'string' ? data.detail : 'Request could not be completed.');
  return data as T;
}
export const SESSION_KEY = 'sevaflow_staff_session';
export const COMMAND_KEY = 'sevaflow_staff_pending';
export function readSaved<T>(key: string): T | null {
  try { return JSON.parse(sessionStorage.getItem(key) || 'null'); } catch { return null; }
}
