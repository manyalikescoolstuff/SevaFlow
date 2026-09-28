export interface Claim {
  token_id: string; display_number: string; status: string; queue_id: string;
  service_id: string; claim_session_id: string; scan_sequence: number | null;
  reservation_expires_at: string; registered_at: string | null; server_time: string;
}
export interface Tracking {
  status: string; people_ahead: number | null; estimated_wait_minutes: number | null;
  counter_label: string | null; server_time: string; recall_attempts: number;
}
export interface BrowserClaim {
  session: string; recovery: string; tracking: string; claimHash?: string;
  tokenId?: string; accepted?: boolean;
}
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
const base = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');
export async function api<T>(path: string, body?: unknown, tracking?: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${base}/customer${path}`, {
      method: body === undefined ? 'GET' : 'POST', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', ...(tracking ? { 'X-Tracking-Secret': tracking } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(15000),
    });
  } catch { throw new ApiError(0, 'Connection interrupted. Please retry.'); }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, typeof result.detail === 'string' ? result.detail : 'Please check your details and try again.');
  return result as T;
}
export function newCredential(): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(32)), n => n.toString(16).padStart(2, '0')).join('');
}
export async function hash(value: string): Promise<string> {
  if (!crypto.subtle) throw new Error('Please open this page over HTTPS or localhost.');
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))), n => n.toString(16).padStart(2, '0')).join('');
}
export async function ownership(saved: BrowserClaim) {
  return { token_id: saved.tokenId, claim_session_id: saved.session, recovery_credential_hash: await hash(saved.recovery) };
}
