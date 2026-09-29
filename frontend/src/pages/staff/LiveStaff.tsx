import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { staffRequest, StaffApiError, SESSION_KEY, COMMAND_KEY, readSaved } from '@/api/staff';
import type { StaffSession, Workstation, PendingCommand, Action } from '@/api/staff';
import './LiveStaff.css';

export function LiveStaffPage() {
  const [session, setSession] = useState(() => readSaved<StaffSession>(SESSION_KEY));
  const [state, setState] = useState<Workstation | null>(null);
  const [pending, setPending] = useState(() => readSaved<PendingCommand>(COMMAND_KEY));
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [stale, setStale] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [now, setNow] = useState(Date.now());
  const [offset, setOffset] = useState(0);
  const commandRunning = useRef(false);
  const epoch = useRef(0);
  const expireSession = useCallback(() => {
    epoch.current += 1;
    sessionStorage.removeItem(SESSION_KEY); setSession(null); setState(null);
    setError('Your session ended. Sign in again to recover any pending action.');
  }, []);
  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    let timer: number;
    const poll = async () => {
      if (!commandRunning.current) {
        const currentEpoch = epoch.current;
        try {
          const data = await staffRequest<Workstation>('/staff/workstation', session);
          if (!cancelled && currentEpoch === epoch.current) {
            setState(data); setStale(false);
            if (data.server_time) setOffset(Date.parse(data.server_time) - Date.now());
          }
        } catch (e) {
          if (!cancelled && currentEpoch === epoch.current) {
            setStale(true); setError((e as Error).message);
            if (e instanceof StaffApiError && e.status === 401) { expireSession(); return; }
          }
        }
      }
      if (!cancelled) timer = window.setTimeout(poll, 3000);
    };
    void poll();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [session, refresh, expireSession]);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const login = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true); setError('');
    try {
      const result = await staffRequest<StaffSession>('/auth/login', undefined,
        new URLSearchParams({ username: String(form.get('username')), password: String(form.get('password')) }));
      if (result.role !== 'STAFF') throw new Error('Use an assigned staff account. Administrators monitor counters.');
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(result));
      setSession(result); setState(null); setStale(true);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  const execute = async (saved: PendingCommand) => {
    if (!session || commandRunning.current || saved.staff_id !== session.staff_id) return;
    commandRunning.current = true; epoch.current += 1; setBusy(true); setError(''); setNotice('');
    try {
      // Save before sending so reload/network failure cannot create a new command.
      sessionStorage.setItem(COMMAND_KEY, JSON.stringify(saved)); setPending(saved);
      await staffRequest(`/staff/counters/${saved.counter_id}/${saved.action}`, session, {
        request_id: saved.request_id, expected_token_id: saved.expected_token_id,
        expected_token_status: saved.expected_token_status,
        expected_recall_attempts: saved.expected_recall_attempts,
      });
      sessionStorage.removeItem(COMMAND_KEY); setPending(null);
      setNotice({ next: 'Counter updated.', start: 'Service started.', pause: 'Counter paused.', resume: 'Counter resumed.', missed: 'Customer marked missed.', 'absent-again': 'Recall absence recorded.' }[saved.action]);
    } catch (e) {
      setError((e as Error).message);
      // A definite 4xx means the backend refused the action. Ambiguous failures
      // retain the original request for an exact retry, even after refreshing.
      if (e instanceof StaffApiError && e.status >= 400 && e.status < 500 && e.status !== 401) {
        sessionStorage.removeItem(COMMAND_KEY); setPending(null);
      }
      if (e instanceof StaffApiError && e.status === 401) expireSession();
    } finally {
      commandRunning.current = false; setBusy(false); setStale(true); setRefresh(n => n + 1);
    }
  };
  const act = (action: Action) => {
    if (!session || !state?.counter || stale || busy || pending) return;
    void execute({ staff_id: session.staff_id, counter_id: state.counter.id, action,
      request_id: crypto.randomUUID(), expected_token_id: state.current_token?.id || null,
      expected_token_status: state.current_token?.status || null,
      ...(action === 'absent-again' ? { expected_recall_attempts: state.current_token?.recall_attempts } : {}) });
  };
  const logout = () => {
    epoch.current += 1; sessionStorage.removeItem(SESSION_KEY); setSession(null); setState(null); setError(''); setNotice('');
  };
  const counter = state?.counter;
  const token = state?.current_token;
  const locked = busy || stale || !!pending || counter?.status === 'CLOSED';
  const elapsed = token?.serving_started_at ? Math.max(0, Math.floor((now + offset - Date.parse(token.serving_started_at)) / 1000)) : 0;
  return <div className="live-staff">
    <header><div><strong>SevaFlow</strong><span>Staff workstation</span></div><nav><Link to="/">Home</Link>{session && <button disabled={busy} onClick={logout}>Sign out</button>}</nav></header>
    <main>
      {error && <div className="live-alert" role="alert">{error}</div>}
      {!session ? <form className="live-card live-login" onSubmit={login}>
        <h1>Staff sign in</h1><p>Operate the counter assigned to your account.</p>
        <label>Username<input name="username" autoComplete="username" required disabled={busy} /></label>
        <label>Password<input name="password" type="password" autoComplete="current-password" required disabled={busy} /></label>
        <button className="live-primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <Link to="/staff/demo">Open demo workstation</Link>
      </form> : <>
        <div className="live-context"><div><h1>{counter?.label || 'Your counter'}</h1><p>{session.name}{counter && ` · ${counter.service_name}`}</p></div><div><span>{stale ? 'Reconnecting…' : 'Live'}</span><button disabled={busy} onClick={() => setRefresh(n => n + 1)}>Refresh</button></div></div>
        {pending && <section className="live-alert"><p>An action is awaiting confirmation. Retrying uses the same request and cannot advance the queue twice.</p>{pending.staff_id === session.staff_id ? <button disabled={busy} onClick={() => void execute(pending)}>Retry saved action</button> : <p>Sign in with the original staff account to resolve this action.</p>}</section>}
        {notice && <p role="status" className="live-notice">{notice}</p>}
        {!state ? <p role="status">Loading your counter…</p> : !counter ? <section className="live-card"><h2>No counter assigned</h2><p>Ask your administrator to assign a counter to this account.</p></section> : <>
          {counter.status !== 'ACTIVE' && <p className="live-alert">Counter {counter.status.toLowerCase()}. New customers will not be assigned.</p>}
          <div className="live-grid"><section className="live-card live-current">
            <p>{token?.status === 'CALLED' ? 'Customer called' : token?.status === 'SERVING' ? 'Now serving' : 'Current token'}</p>
            <div className="live-token">{token?.display_number || '—'}</div>
            <p>{token ? `${token.status}${token.is_recall ? ' · Recall' : ''}` : 'Counter is free'}</p>
            {token?.status === 'SERVING' && <p>Service time <strong>{String(Math.floor(elapsed / 60)).padStart(2, '0')}:{String(elapsed % 60).padStart(2, '0')}</strong></p>}
            {!token && <button className="live-primary" disabled={locked || counter.status !== 'ACTIVE'} onClick={() => act('next')}>Call Next</button>}
            {token?.status === 'CALLED' && <button className="live-primary" disabled={locked || counter.status !== 'ACTIVE'} onClick={() => act('start')}>Start Service</button>}
            {token?.status === 'CALLED' && <button disabled={locked} onClick={() => act(token.is_recall ? 'absent-again' : 'missed')}>{token.is_recall ? token.recall_attempts >= 1 ? 'Absent — close token & next' : 'Absent again & next' : 'Mark Missed & Next'}</button>}
            {token?.status === 'SERVING' && <button className="live-primary" disabled={locked} onClick={() => act('next')}>{counter.status === 'PAUSED' ? 'Complete Service' : 'Complete & Next'}</button>}
            <button disabled={locked} onClick={() => act(counter.status === 'PAUSED' ? 'resume' : 'pause')}>{counter.status === 'PAUSED' ? 'Resume counter' : 'Pause counter'}</button>
            {token?.status === 'CALLED' && <p className="live-hint">{token.is_recall ? `Recall ${token.recall_attempts + 1} of 2. ${token.recall_attempts >= 1 ? 'Marking absent closes this token; the customer must request a new one.' : 'If absent, the token waits for another service to finish before recall.'}` : 'Start service when the customer is present. Mark missed only after giving them time to arrive.'}</p>}
          </section><aside className="live-card"><h2>Waiting queue <span>{state.waiting_count}</span></h2><p>Registered customers, ordered by scan priority.</p><ol className="live-upcoming">{state.upcoming?.map(t => <li key={t.id}><strong>{t.display_number}</strong><span>Waiting</span></li>)}</ol>{!state.upcoming?.length && <p>No registered customers waiting.</p>}
            {!!state.missed?.length && <section><h2>Awaiting recall</h2><ul className="live-upcoming">{state.missed.map(t => <li key={t.id}><strong>{t.display_number}</strong><span>{t.recall_attempts}/2 recalls missed</span></li>)}</ul><p>A missed token stays open while waiting for another service to finish.</p></section>}
            <div className="live-total"><strong>{counter.served_today}</strong><span>Services completed</span></div></aside></div>
        </>}
      </>}
    </main>
  </div>;
}
