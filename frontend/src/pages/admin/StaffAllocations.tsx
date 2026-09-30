import { useEffect, useState, type FormEvent } from 'react';
import { staffRequest } from '@/api/staff';
import { useLiveAdmin } from './LiveAdmin';
import '../staff/LiveStaff.css';

type Allocation = { id: string; staff_id: string; counter_id: string; starts_at: string; ends_at: string; status: string };
type Schedule = { staff: { id: string; name: string }[]; counters: { id: string; label: string; staff_id: string | null; busy: boolean }[]; allocations: Allocation[]; server_time: string };
const format = (value: string) => new Date(value).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });

export function StaffAllocationsPage() {
  const { session } = useLiveAdmin();
  const [data, setData] = useState<Schedule | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const value = await staffRequest<Schedule>('/admin/allocations', session);
        if (!cancelled) setData(value);
      } catch (e) { if (!cancelled) setError((e as Error).message); }
      if (!cancelled) timer = setTimeout(load, 10000);
    };
    void load();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [session, refresh]);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!session || busy) return;
    const form = event.currentTarget;
    const values = new FormData(form);
    setBusy(true); setError(''); setNotice('');
    try {
      await staffRequest('/admin/allocations', session, {
        id: requestId, staff_id: values.get('staff'), counter_id: values.get('counter'),
        starts_at: new Date(`${values.get('start')}:00+05:30`).toISOString(),
        ends_at: new Date(`${values.get('end')}:00+05:30`).toISOString(),
      });
      form.reset(); setRequestId(crypto.randomUUID()); setRefresh(n => n + 1);
      setNotice('Allocation scheduled. Apply it during its time slot when both counters are free.');
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  const act = async (id: string, action: string) => {
    if (!session || busy) return;
    setBusy(true); setError(''); setNotice('');
    try {
      await staffRequest(`/admin/allocations/${id}/${action}`, session, {});
      setNotice(action === 'release' ? 'Previous assignments restored. Staff can resume paused counters when ready.' : `Allocation ${action === 'apply' ? 'applied' : 'cancelled'}.`);
      setRefresh(n => n + 1);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  return <div className="live-staff"><h1>Staff allocation</h1>
    <p>Schedule a staff member at a counter for a specific date and time. All times are India time (IST).</p>
    <p>Admins apply allocations when due and free, then release them to restore previous assignments. End times do not interrupt service or release staff automatically.</p>
    {error && <p role="alert" className="live-alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {!data ? <p>Loading staff and counters…</p> : <>
      <form className="live-card live-login" onSubmit={submit} onChange={() => setRequestId(crypto.randomUUID())}>
        <label>Staff member<select name="staff" required disabled={busy}><option value="">Choose staff</option>{data.staff.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
        <label>Destination counter<select name="counter" required disabled={busy}><option value="">Choose counter</option>{data.counters.map(c => <option key={c.id} value={c.id}>{c.label} · {c.busy ? 'busy now' : 'free now'}</option>)}</select></label>
        <label>Start (IST)<input name="start" type="datetime-local" required disabled={busy}/></label>
        <label>End (IST)<input name="end" type="datetime-local" required disabled={busy}/></label>
        <button className="live-primary" disabled={busy}>Schedule allocation</button>
      </form>
      <h2>Scheduled and active allocations</h2>
      <div className="admin-table-wrapper"><table className="admin-table"><thead><tr><th>Staff</th><th>Counter</th><th>Start (IST)</th><th>End (IST)</th><th>Status</th><th>Actions</th></tr></thead><tbody>
        {data.allocations.map(a => {
          const now = Date.parse(data.server_time);
          const due = Date.parse(a.starts_at) <= now && now < Date.parse(a.ends_at);
          return <tr key={a.id}><td>{data.staff.find(s => s.id === a.staff_id)?.name || a.staff_id}</td><td>{data.counters.find(c => c.id === a.counter_id)?.label || a.counter_id}</td><td>{format(a.starts_at)}</td><td>{format(a.ends_at)}</td><td>{a.status}{a.status === 'SCHEDULED' && now >= Date.parse(a.ends_at) ? ' · expired' : a.status === 'ACTIVE' && now >= Date.parse(a.ends_at) ? ' · release due' : ''}</td><td>
            {a.status === 'SCHEDULED' && <><button disabled={busy || !due} onClick={() => act(a.id, 'apply')}>Apply when free</button> <button disabled={busy} onClick={() => act(a.id, 'cancel')}>Cancel</button></>}
            {a.status === 'ACTIVE' && <button disabled={busy} onClick={() => act(a.id, 'release')}>Release / restore</button>}
          </td></tr>;
        })}
      </tbody></table></div>
      {!data.allocations.length && <p>No allocations scheduled yet.</p>}
    </>}
  </div>;
}
