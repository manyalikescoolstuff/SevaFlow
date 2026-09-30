import { createContext, useContext, useEffect, useState, useCallback, type FormEvent, type ReactNode } from 'react';
import { staffRequest, StaffApiError, readSaved, type StaffSession } from '@/api/staff';
import { useLocation } from 'react-router-dom';
import '../staff/LiveStaff.css';
import './Overview.css';

export interface AdminSnapshot {
  server_time: string; report_date: string; timezone: string;
  registered_today: number; completed_today: number; waiting_now: number; active_counters: number;
  queues: { id: string; service_name: string; waiting: number; missed: number; called: number; serving: number;
    active_counters: number; total_counters: number; estimated_wait_minutes: number | null;
    upcoming: { id: string; display_number: string }[] }[];
  counters: { id: string; label: string; service_name: string; status: string; staff_name: string | null;
    token_number: string | null; token_status: string | null; serving_started_at: string | null; recorded_completions: number }[];
}
const KEY = 'sevaflow_admin_session';
const Context = createContext<{ data: AdminSnapshot | null; stale: boolean; logout: () => void; session: StaffSession | null }>({ data: null, stale: true, logout: () => {}, session: null });
export const useLiveAdmin = () => useContext(Context);

export function AdminAccess({ children }: { children: ReactNode }) {
  const { pathname, search } = useLocation();
  const demo = /\/admin\/demo(\/|$)/.test(pathname) || (pathname === '/admin/predictions' && new URLSearchParams(search).get('preview') === '1');
  const [session, setSession] = useState(() => readSaved<StaffSession>(KEY));
  const [data, setData] = useState<AdminSnapshot | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [stale, setStale] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const logout = useCallback(() => { sessionStorage.removeItem(KEY); setSession(null); setData(null); setError(''); setStale(true); }, []);
  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    let timer: number;
    const poll = async () => {
      try {
        const value = await staffRequest<AdminSnapshot>('/admin/monitor', session);
        if (!cancelled) { setData(value); setStale(false); setError(''); }
      } catch (e) {
        if (!cancelled) {
          setStale(true); setError((e as Error).message);
          if (e instanceof StaffApiError && [401, 403].includes(e.status)) {
            sessionStorage.removeItem(KEY); setSession(null); setData(null); return;
          }
        }
      }
      if (!cancelled) timer = window.setTimeout(poll, 5000);
    };
    void poll();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [session, refresh]);
  const login = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError('');
    const form = new FormData(event.currentTarget);
    try {
      const value = await staffRequest<StaffSession>('/auth/login', undefined, new URLSearchParams({
        username: String(form.get('username')), password: String(form.get('password')) }));
      if (value.role !== 'ADMIN') throw new Error('Sign in with an administrator account. Staff use the staff workstation.');
      sessionStorage.setItem(KEY, JSON.stringify(value)); setSession(value); setStale(true);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  if (!session) return <div className="live-staff"><main>
    {error && <p role="alert" className="live-alert">{error}</p>}
    <form className="live-card live-login" onSubmit={login}><h1>Administrator sign in</h1><p>Monitor services, queues, and counters.</p>
      <label>Username<input name="username" autoComplete="username" required disabled={busy}/></label>
      <label>Password<input name="password" type="password" autoComplete="current-password" required disabled={busy}/></label>
      <button className="live-primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
    </form></main></div>;
  return <Context.Provider value={{data, stale, logout, session}}><div className="admin-access">
    {pathname !== '/admin/staff-allocation' ? (
      <div className="admin-connection" role="status">
        <span>{demo ? 'Demo page · sample data' : pathname === '/admin/predictions' ? 'Demand baseline · coverage and limitations shown below' : pathname === '/admin/analytics' ? 'Historical analytics · report status shown below' : stale ? 'Reconnecting — showing last available data' : 'Live · updates every 5 seconds'}{!demo && !['/admin/analytics', '/admin/predictions'].includes(pathname) && data && ` · ${data.report_date} (${data.timezone})`}</span>
        <button onClick={() => setRefresh(n => n + 1)}>Refresh</button>
        {error && <span role="alert">{error}</span>}
      </div>
    ) : (
      error ? <div className="admin-connection" role="status"><span role="alert">{error}</span></div> : null
    )}
    {children}
  </div></Context.Provider>;
}

export function LiveAdminPage({ view }: { view: 'Overview' | 'Queues' | 'Counters' }) {
  const { data } = useLiveAdmin();
  if (!data) return <p role="status">Loading monitoring data…</p>;
  return <div className="admin-overview"><header className="admin-overview__header"><div><h1 className="admin-overview__title">{view}</h1><p>Service centre monitoring</p></div></header>
    <section className="admin-overview__metrics" aria-label="Operational summary">{[
      ['Registered today', data.registered_today], ['Completed today', data.completed_today],
      ['Waiting now', data.waiting_now], ['Active counters', `${data.active_counters} / ${data.counters.length}`],
    ].map(([label, value]) => <div className="admin-metric-card" key={label}><span className="admin-metric-card__label">{label}</span><strong className="admin-metric-card__value">{value}</strong></div>)}</section>
    {view !== 'Counters' && <section className="admin-overview__section"><h2 className="admin-overview__section-title">Live queues</h2>
      {!data.queues.length ? <p>No service queues configured.</p> : <div className="admin-table-wrapper"><table className="admin-table"><thead><tr><th>Service</th><th>Waiting</th><th>Called</th><th>Serving</th><th>Missed</th><th>Est. wait</th><th>Counters active / total</th></tr></thead><tbody>
        {data.queues.map(q => <tr key={q.id}><td className="admin-table__service-name">{q.service_name}</td><td>{q.waiting}</td><td>{q.called}</td><td>{q.serving}</td><td>{q.missed}</td><td>{q.estimated_wait_minutes === null ? 'Unavailable' : `About ${q.estimated_wait_minutes} min`}</td><td>{q.active_counters} / {q.total_counters}</td></tr>)}
      </tbody></table></div>}<p>Estimates are approximate for the end of each waiting line. Recalls and service durations can change them.</p>
      {view === 'Queues' && data.queues.map(q => <details className="admin-live-detail" key={q.id}><summary>{q.service_name} — next registered tokens</summary><p>{q.upcoming.map(t => t.display_number).join(' → ') || 'No registered customers waiting.'}</p><small>Scan order; due recalls may take precedence.</small></details>)}
    </section>}
    {view !== 'Queues' && <section className="admin-overview__section"><h2 className="admin-overview__section-title">Counters</h2>
      {!data.counters.length ? <p>No counters configured.</p> : <div className="admin-counters-grid">{data.counters.map(c => <article className="admin-counter-card" key={c.id}>
        <div className="admin-counter-card__top"><strong>{c.label}</strong><span className={`counter-pill counter-pill--${c.status === 'ACTIVE' ? 'active' : 'paused'}`}>{c.status}</span></div>
        <p className="admin-counter-card__service">{c.service_name}</p><div className="admin-counter-card__divider"/>
        <p className="admin-counter-card__serving">{c.token_status || 'Free'}: <strong>{c.token_number || '—'}</strong></p>
        <p>Staff: {c.staff_name || 'Unassigned'}</p><small>{c.recorded_completions} recorded completions</small>
      </article>)}</div>}<p>Recorded counter completions are cumulative until reset; the daily total above uses completed-token timestamps.</p>
    </section>}
  </div>;
}

export function AdminDemoNotice({ children }: { children: ReactNode }) {
  return <><p className="admin-demo-notice" role="note">Demo only — the figures below use sample data, not live service-centre records.</p>{children}</>;
}
