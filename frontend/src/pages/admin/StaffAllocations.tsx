import { useEffect, useState, useMemo, type FormEvent } from 'react';
import { staffRequest, StaffApiError } from '@/api/staff';
import { useLiveAdmin } from './LiveAdmin';
import './StaffAllocations.css';

type Allocation = { id: string; staff_id: string; counter_id: string; starts_at: string; ends_at: string; status: string };
type Schedule = { staff: { id: string; name: string }[]; counters: { id: string; label: string; staff_id: string | null; busy: boolean }[]; allocations: Allocation[]; server_time: string };

const formatTime = (value: string) => new Date(value).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' });
const formatDate = (value: string) => new Date(value).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short' });
const formatDateTime = (value: string) => `${formatDate(value)}, ${formatTime(value)}`;

function getDurationMinutes(start: string, end: string) {
  const ms = Date.parse(end) - Date.parse(start);
  return Math.round(ms / 60000);
}

function toISTDateString(isoString: string) {
  return new Date(isoString).toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' }); // YYYY-MM-DD
}

export function StaffAllocationsPage() {
  const { session, logout } = useLiveAdmin();
  const [data, setData] = useState<Schedule | null>(null);
  
  const [loadingError, setLoadingError] = useState('');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  
  const [busy, setBusy] = useState(false);
  const [stale, setStale] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  
  const [showForm, setShowForm] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const endpoint = demoMode ? '/admin/demo-allocations' : '/admin/allocations';
  
  const toggleDemoMode = () => {
    setDemoMode(prev => !prev);
    setData(null);
    setLoadingError('');
    setActionError('');
    setNotice('');
    setShowForm(false);
    setRequestId(crypto.randomUUID());
  };
  
  // Filters
  const [filterDate, setFilterDate] = useState('');
  const [filterStaff, setFilterStaff] = useState('');
  const [filterCounter, setFilterCounter] = useState('');
  const [activeTab, setActiveTab] = useState<'Scheduled' | 'Active' | 'History'>('Scheduled');

  // Form local state
  const [formStaff, setFormStaff] = useState('');
  const [formCounter, setFormCounter] = useState('');
  
  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    let timer: number;
    const load = async () => {
      try {
        const value = await staffRequest<Schedule>(endpoint, session);
        if (!cancelled) {
          setData(value);
          setLoadingError('');
          setStale(false);
          setLastRefreshed(new Date());
        }
      } catch (e) {
        if (!cancelled) {
          const err = e as StaffApiError;
          setLoadingError(err.message);
          setStale(true);
          if (err.status === 401 || err.status === 403) logout();
        }
      }
      if (!cancelled) timer = window.setTimeout(load, 10000);
    };
    void load();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [session, refresh, logout, endpoint]);

  const serverTime = data ? Date.parse(data.server_time) : Date.now();
  
  const filteredAllocations = useMemo(() => {
    if (!data) return [];
    return data.allocations.filter(a => {
      if (filterStaff && a.staff_id !== filterStaff) return false;
      if (filterCounter && a.counter_id !== filterCounter) return false;
      
      if (filterDate) {
        const startDay = toISTDateString(a.starts_at);
        const endDay = toISTDateString(a.ends_at);
        if (filterDate < startDay || filterDate > endDay) return false;
      }
      return true;
    });
  }, [data, filterStaff, filterCounter, filterDate]);

  const scheduled = filteredAllocations.filter(a => a.status === 'SCHEDULED');
  const active = filteredAllocations.filter(a => a.status === 'ACTIVE');
  const history = filteredAllocations.filter(a => a.status === 'COMPLETED' || a.status === 'CANCELLED');
  
  scheduled.sort((a, b) => {
    const aDue = Date.parse(a.starts_at) <= serverTime;
    const bDue = Date.parse(b.starts_at) <= serverTime;
    if (aDue && !bDue) return -1;
    if (!aDue && bDue) return 1;
    return Date.parse(a.starts_at) - Date.parse(b.starts_at);
  });
  
  active.sort((a, b) => {
    const aOverdue = Date.parse(a.ends_at) <= serverTime;
    const bOverdue = Date.parse(b.ends_at) <= serverTime;
    if (aOverdue && !bOverdue) return -1;
    if (!aOverdue && bOverdue) return 1;
    return Date.parse(a.starts_at) - Date.parse(b.starts_at);
  });
  
  history.sort((a, b) => Date.parse(b.starts_at) - Date.parse(a.starts_at));

  const currentTabAllocations = activeTab === 'Scheduled' ? scheduled : activeTab === 'Active' ? active : history;

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!session || busy) return;
    const form = event.currentTarget;
    const values = new FormData(form);
    
    const startIso = new Date(`${values.get('start')}:00+05:30`).toISOString();
    const endIso = new Date(`${values.get('end')}:00+05:30`).toISOString();
    
    if (Date.parse(endIso) <= Date.parse(startIso)) {
      setActionError('End time must be after start time.');
      return;
    }
    if (Date.parse(endIso) <= serverTime) {
      setActionError('End time must be in the future.');
      return;
    }
    
    if (data) {
      const staffId = values.get('staff') as string;
      const counterId = values.get('counter') as string;
      const proposedStart = Date.parse(startIso);
      const proposedEnd = Date.parse(endIso);
      
      const overlap = data.allocations.some(a => 
        (a.status === 'SCHEDULED' || a.status === 'ACTIVE') &&
        (a.staff_id === staffId || a.counter_id === counterId) &&
        Date.parse(a.starts_at) < proposedEnd && Date.parse(a.ends_at) > proposedStart
      );
      if (overlap) {
        setActionError('Allocation overlaps with an existing scheduled or active booking for this staff or counter.');
        return;
      }
    }
    
    setBusy(true); setActionError(''); setNotice('');
    try {
      await staffRequest(endpoint, session, {
        id: requestId, staff_id: values.get('staff'), counter_id: values.get('counter'),
        starts_at: startIso,
        ends_at: endIso,
      });
      form.reset(); 
      setFormStaff(''); setFormCounter('');
      setRequestId(crypto.randomUUID()); 
      setRefresh(n => n + 1);
      setShowForm(false);
      setNotice('Allocation scheduled.');
    } catch (e) { 
      const err = e as StaffApiError;
      setActionError(err.message);
      if (err.status === 401 || err.status === 403) logout();
    }
    finally { setBusy(false); }
  };
  
  const act = async (id: string, action: string) => {
    if (!session || busy) return;
    setBusy(true); setActionError(''); setNotice('');
    try {
      await staffRequest(`${endpoint}/${id}/${action}`, session, {});
      setNotice(action === 'release' ? 'Previous assignments restored. Staff can resume paused counters when ready.' : `Allocation ${action === 'apply' ? 'applied' : 'cancelled'}.`);
      setRefresh(n => n + 1);
    } catch (e) { 
      const err = e as StaffApiError;
      setActionError(err.message);
      if (err.status === 401 || err.status === 403) logout();
    }
    finally { setBusy(false); }
  };

  return (
    <div className="staff-allocations-layout">
      <header className="staff-allocations-header">
        <div className="header-text">
          <h1>Staff allocation</h1>
          <p>Schedule staff members to specific counters for time-bound assignments.</p>
        </div>
        <div className="header-actions">
          <button className="live-secondary" onClick={toggleDemoMode} disabled={busy}>
            {demoMode ? 'Switch to live data' : 'Try Demo Mode'}
          </button>
          <button className="live-primary" onClick={() => setShowForm(!showForm)} disabled={busy}>
            {showForm ? 'Close form' : 'Schedule allocation'}
          </button>
        </div>
      </header>

      {demoMode && (
        <div className="demo-mode-banner" role="status">
          <strong>Demo Mode Active</strong> — Sample data — changes do not affect live operations.
        </div>
      )}

      <div className="allocations-freshness" role="status">
        <span>
          {stale ? 'Reconnecting — showing last available data' : 'Live · updates every 10 seconds'}
          {!stale && lastRefreshed && ` · Last checked ${lastRefreshed.toLocaleTimeString()}`}
        </span>
        <button onClick={() => setRefresh(n => n + 1)}>Refresh</button>
        {loadingError && <span role="alert" className="error-text"> · {loadingError}</span>}
      </div>

      {actionError && <p role="alert" className="allocations-alert allocations-alert--error">{actionError}</p>}
      {notice && <p role="status" className="allocations-alert allocations-alert--success">{notice}</p>}

      {showForm && data && (
        <form className="allocations-form-panel" onSubmit={submit} onChange={() => setRequestId(crypto.randomUUID())}>
          <h2>New allocation</h2>
          <div className="form-row">
            <label>
              Staff member
              <select name="staff" required disabled={busy} value={formStaff} onChange={e => setFormStaff(e.target.value)}>
                <option value="">Choose staff</option>
                {data.staff.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </label>
            <label>
              Destination counter
              <select name="counter" required disabled={busy} value={formCounter} onChange={e => setFormCounter(e.target.value)}>
                <option value="">Choose counter</option>
                {data.counters.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
              </select>
            </label>
          </div>
          
          {(formStaff || formCounter) && (
            <div className="form-info">
              {formStaff && <p><strong>Staff {data.staff.find(s=>s.id === formStaff)?.name}:</strong> {
                data.allocations.some(a => a.status === 'ACTIVE' && a.staff_id === formStaff) ? 'Currently active in an allocation.' :
                data.counters.some(c => c.staff_id === formStaff) ? 'Assigned to a counter.' : 'Available.'
              }</p>}
              {formCounter && (() => {
                 const c = data.counters.find(x => x.id === formCounter);
                 if (!c) return null;
                 return <p><strong>Counter {c.label}:</strong> {c.busy ? 'Busy serving.' : c.staff_id ? 'Staffed but free.' : 'Unstaffed.'}</p>;
              })()}
            </div>
          )}

          <div className="form-row">
            <label>Start (IST)<input name="start" type="datetime-local" required disabled={busy}/></label>
            <label>End (IST)<input name="end" type="datetime-local" required disabled={busy}/></label>
          </div>
          <div className="form-actions">
            <button type="submit" className="live-primary" disabled={busy}>Schedule</button>
            <button type="button" onClick={() => setShowForm(false)} disabled={busy}>Cancel</button>
          </div>
        </form>
      )}

      <div className="allocations-toolbar">
        <div className="toolbar-filters">
          <label>
            Date (IST)
            <input type="date" value={filterDate} onChange={e => setFilterDate(e.target.value)} />
          </label>
          <label>
            Staff
            <select value={filterStaff} onChange={e => setFilterStaff(e.target.value)}>
              <option value="">All staff</option>
              {data?.staff.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          <label>
            Counter
            <select value={filterCounter} onChange={e => setFilterCounter(e.target.value)}>
              <option value="">All counters</option>
              {data?.counters.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </label>
        </div>
        <div className="toolbar-tabs">
          <button className={activeTab === 'Scheduled' ? 'active' : ''} onClick={() => setActiveTab('Scheduled')}>Scheduled ({scheduled.length})</button>
          <button className={activeTab === 'Active' ? 'active' : ''} onClick={() => setActiveTab('Active')}>Active ({active.length})</button>
          <button className={activeTab === 'History' ? 'active' : ''} onClick={() => setActiveTab('History')}>History ({history.length})</button>
        </div>
      </div>

      <div className="allocations-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Staff</th>
              <th>Destination counter</th>
              <th>Start–End (IST)</th>
              <th>Duration</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {!data ? <tr><td colSpan={6}>Loading...</td></tr> : 
             currentTabAllocations.length === 0 ? <tr><td colSpan={6} className="empty-state">No allocations found.</td></tr> :
             currentTabAllocations.map(a => {
              const startParse = Date.parse(a.starts_at);
              const endParse = Date.parse(a.ends_at);
              const isDue = startParse <= serverTime;
              const isExpired = endParse <= serverTime;
              const duration = getDurationMinutes(a.starts_at, a.ends_at);
              
              const sName = data.staff.find(s => s.id === a.staff_id)?.name || a.staff_id;
              const cName = data.counters.find(c => c.id === a.counter_id)?.label || a.counter_id;
              
              let applyDisabledReason = '';
              if (a.status === 'SCHEDULED' && isDue && !isExpired) {
                 const destCounter = data.counters.find(c => c.id === a.counter_id);
                 if (destCounter?.busy) {
                   applyDisabledReason = 'Destination counter is busy';
                 } else {
                   const staffCurrentCounter = data.counters.find(c => c.staff_id === a.staff_id);
                   if (staffCurrentCounter?.busy) {
                     applyDisabledReason = 'Staff is currently serving a customer';
                   }
                 }
              }

              return (
                <tr key={a.id}>
                  <td>{sName}</td>
                  <td>{cName}</td>
                  <td>
                    <div className="time-range">{formatDateTime(a.starts_at)} <br/>to {formatTime(a.ends_at)}</div>
                  </td>
                  <td>{duration} min</td>
                  <td>
                    <span className={`status-badge status-${a.status.toLowerCase()}`}>
                      {a.status}
                    </span>
                    {a.status === 'SCHEDULED' && isExpired && <div className="timing-annotation">Expired</div>}
                    {a.status === 'ACTIVE' && isExpired && <div className="timing-annotation overdue">Release due</div>}
                    {a.status === 'SCHEDULED' && isDue && !isExpired && <div className="timing-annotation due">Due</div>}
                  </td>
                  <td>
                    <div className="action-buttons">
                      {a.status === 'SCHEDULED' && (
                        <>
                          <button 
                            disabled={busy || !isDue || isExpired || !!applyDisabledReason} 
                            title={applyDisabledReason || (isExpired ? 'Cannot apply expired schedule' : !isDue ? 'Not due yet' : 'Apply')}
                            onClick={() => act(a.id, 'apply')}>
                            Apply
                          </button>
                          <button disabled={busy} onClick={() => act(a.id, 'cancel')}>Cancel</button>
                        </>
                      )}
                      {a.status === 'ACTIVE' && (
                        <button disabled={busy} onClick={() => act(a.id, 'release')}>
                          Release
                        </button>
                      )}
                      {(a.status === 'COMPLETED' || a.status === 'CANCELLED') && (
                        <span className="no-actions">—</span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
