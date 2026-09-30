import { useEffect, useState } from 'react';
import { staffRequest, StaffApiError } from '@/api/staff';
import { useLiveAdmin } from './LiveAdmin';
import './Analytics.css';

interface Metrics { registrations: number; completions: number; avg_wait_seconds: number | null; wait_samples: number; avg_service_seconds: number | null; service_samples: number }
interface Analytics {
  report_date: string; timezone: string; partial_day: boolean; server_time: string;
  summary: Metrics; hourly: (Metrics & { hour: number })[];
  services: (Metrics & { service_id: string; service_name: string })[];
  utilization_percent: number | null; utilization_note: string;
}
const duration = (seconds: number | null) => seconds === null ? 'Unavailable' : `${Math.floor(Math.round(seconds) / 60)}m ${Math.round(seconds) % 60}s`;
const hourLabel = (hour: number) => `${String(hour).padStart(2, '0')}:00`;

export function LiveAnalyticsPage() {
  const { session, logout, data: monitor } = useLiveAdmin();
  const [date, setDate] = useState('');
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    let timer: number;
    const poll = async () => {
      try {
        const result = await staffRequest<Analytics>(`/admin/analytics${date ? `?date=${encodeURIComponent(date)}` : ''}`, session);
        if (!cancelled) { setData(result); setError(''); }
      } catch (e) {
        if (!cancelled) {
          setError((e as Error).message);
          if (e instanceof StaffApiError && [401, 403].includes(e.status)) { logout(); return; }
        }
      }
      if (!cancelled) timer = window.setTimeout(poll, 15000);
    };
    void poll();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [session, date, refresh, logout]);
  const max = Math.max(1, ...(data?.hourly.map(h => h.registrations) || []));
  const peak = data?.hourly.filter(h => h.registrations === max && h.registrations > 0) || [];
  return <div className="admin-analytics">
    <header className="admin-analytics__header"><div><h1 className="admin-analytics__title">Analytics</h1><p>Recorded activity · Asia/Kolkata calendar day</p></div>
      <div className="analytics-date-controls"><label>Report date <input type="date" value={date || monitor?.report_date || ''} max={monitor?.report_date} onChange={e => {setDate(e.target.value); setData(null); setError('');}} /></label>
        <button onClick={() => {setDate(''); setData(null); setError(''); setRefresh(n => n + 1);}}>Today</button><button onClick={() => setRefresh(n => n + 1)}>Refresh analytics</button></div>
    </header>
    {error && <p role="alert" className="admin-demo-notice">{error}{data && ' Showing the last successful report.'}</p>}
    {!data ? <p role="status">{error ? 'Report unavailable. Retry with Refresh analytics.' : 'Loading report…'}</p> : <>
      <p role="status">{data.report_date}{data.partial_day ? ' · Today so far' : ' · Full calendar day'} · {error ? 'Update interrupted' : 'Refreshes every 15 seconds'}</p>
      <section className="admin-analytics__kpis" aria-label="Analytics summary">{[
        ['Registrations', data.summary.registrations, 'Completed name and phone registration'],
        ['Completions', data.summary.completions, 'Services completed on this date'],
        ['Average wait', duration(data.summary.avg_wait_seconds), `${data.summary.wait_samples} completed services with valid timestamps`],
        ['Average service', duration(data.summary.avg_service_seconds), `${data.summary.service_samples} completed services with valid timestamps`],
      ].map(([label,value,note]) => <div className="admin-metric-card" key={label}><span className="admin-metric-card__label">{label}</span><strong className="admin-metric-card__value">{value}</strong><span className="admin-metric-card__subtext">{note}</span></div>)}</section>
      {data.summary.registrations === 0 && data.summary.completions === 0 && <p>No registrations or completed services recorded for this date.</p>}
      <section className="admin-chart-card" aria-label="Hourly registrations"><h2 className="admin-chart-card__title">Registrations by hour</h2>
        <p>{peak.length ? `Peak hour${peak.length > 1 ? 's' : ''}: ${peak.map(h => hourLabel(h.hour)).join(', ')} · ${max} registrations each` : 'No peak hour — no registrations recorded.'}</p>
        <div className="analytics-hourly-scroll"><div className="analytics-hourly-bars">{data.hourly.map(h => <div className="analytics-hour" key={h.hour} title={`${hourLabel(h.hour)}: ${h.registrations} registrations`}><span>{h.registrations}</span><div className="analytics-hour-track"><div style={{height:`${h.registrations / max * 100}%`}} /></div><small>{String(h.hour).padStart(2,'0')}</small></div>)}</div></div>
      </section>
      <section className="admin-analytics__table-section"><h2 className="admin-analytics__table-title">Service performance</h2><div className="admin-analytics__table-wrapper"><table className="admin-analytics__table"><thead><tr><th>Service</th><th>Registrations</th><th>Completions</th><th>Average wait</th><th>Wait samples</th><th>Average service</th><th>Service samples</th></tr></thead><tbody>{data.services.map(s => <tr key={s.service_id}><td>{s.service_name}</td><td>{s.registrations}</td><td>{s.completions}</td><td>{duration(s.avg_wait_seconds)}</td><td>{s.wait_samples}</td><td>{duration(s.avg_service_seconds)}</td><td>{s.service_samples}</td></tr>)}</tbody></table></div>{!data.services.length && <p>No services configured.</p>}</section>
      <details className="admin-live-detail"><summary>Hourly counts and measured durations</summary><div className="admin-analytics__table-wrapper"><table className="admin-analytics__table"><thead><tr><th>Hour</th><th>Registrations</th><th>Completions</th><th>Average wait</th><th>Wait samples</th><th>Average service</th><th>Service samples</th></tr></thead><tbody>{data.hourly.map(h => <tr key={h.hour}><td>{hourLabel(h.hour)}</td><td>{h.registrations}</td><td>{h.completions}</td><td>{duration(h.avg_wait_seconds)}</td><td>{h.wait_samples}</td><td>{duration(h.avg_service_seconds)}</td><td>{h.service_samples}</td></tr>)}</tbody></table></div></details>
      <section className="admin-chart-card"><h2 className="admin-chart-card__title">How these metrics are counted</h2><p>Registrations use registration time. Completed services and their averages use completion time, so they may include customers registered on an earlier date.</p><p>Wait is registration to actual service start, including missed-turn and recall delays. Service duration is start to completion, including any pause. Missing or invalid timestamps are excluded from averages; no samples means unavailable, not zero.</p><p>Counter utilization: unavailable. {data.utilization_note}</p></section>
    </>}
  </div>;
}
