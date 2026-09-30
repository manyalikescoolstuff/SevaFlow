import { useEffect, useState } from 'react';
import { staffRequest, StaffApiError } from '@/api/staff';
import { useLiveAdmin } from './LiveAdmin';
import './Predictions.css';
import './Analytics.css';

interface Forecast {
  forecast_date: string; timezone: string; generated_at: string; status: 'available' | 'insufficient_data'; reason: string | null;
  method: string; window_start: string; window_end: string; recorded_days: number; required_days: number;
  days_without_records: number; latest_recorded_date: string | null; registration_samples: number;
  expected_registrations: number | null; historical_daily_min: number | null; historical_daily_max: number | null;
  hourly: { hour: number; expected_registrations: number }[];
  services: { service_id: string; service_name: string; recorded_days: number; expected_registrations: number | null }[];
  limitations: string[];
}

export function LivePredictionsPage() {
  const { session, logout } = useLiveAdmin();
  const [data, setData] = useState<Forecast | null>(null);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    let timer: number;
    const poll = async () => {
      try {
        const result = await staffRequest<Forecast>('/admin/predictions', session);
        if (!cancelled) { setData(result); setError(''); }
      } catch (e) {
        if (!cancelled) {
          setError((e as Error).message);
          if (e instanceof StaffApiError && [401,403].includes(e.status)) { logout(); return; }
        }
      }
      if (!cancelled) timer = window.setTimeout(poll, 60000);
    };
    void poll();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [session, logout, refresh]);
  const max = Math.max(1, ...(data?.hourly.map(h => h.expected_registrations) || []));
  return <div className="admin-predictions">
    <header className="admin-predictions__header"><div><h1 className="admin-predictions__title">Predictions</h1><p>Next-day demand · provisional recorded-day baseline</p></div><div className="analytics-date-controls"><button onClick={() => setRefresh(n => n + 1)}>Refresh forecast</button></div></header>
    {error && <p role="alert" className="admin-demo-notice">{error}{data && ' Showing the last successful forecast response.'}</p>}
    {!data ? <p role="status">{error ? 'Forecast unavailable. Retry with Refresh forecast.' : 'Checking recorded history…'}</p> : <>
      <p role="status">For {data.forecast_date} · {data.timezone} · {error ? 'Update interrupted' : 'Refreshes every minute'}</p>
      {data.status !== 'available' && <section className="admin-chart-card"><h2 className="admin-chart-card__title">Not enough recent history</h2><p>{data.reason}</p><p>Continue recording real registrations. Sample/demo data is never substituted for missing history.</p></section>}
      <section className="admin-predictions__kpis" aria-label="Forecast summary">{[
        ['Expected registrations', data.expected_registrations ?? 'Unavailable', 'Mean per recorded day, conditional on similar activity'],
        ['Recorded days', `${data.recorded_days} / ${data.required_days} minimum`, `${data.registration_samples} registrations in the lookback window`],
        ['Observed daily range', data.historical_daily_min === null ? 'Unavailable' : `${data.historical_daily_min}–${data.historical_daily_max}`, 'Historical range, not a forecast confidence interval'],
        ['Expected wait', 'Unavailable', 'Future staffing and opening hours are not recorded'],
      ].map(([label,value,note]) => <article className="admin-metric-card" key={label}><span className="admin-metric-card__label">{label}</span><strong className="admin-metric-card__value">{value}</strong><span className="admin-metric-card__subtext">{note}</span></article>)}</section>
      {!!data.hourly.length && <section className="admin-chart-card" aria-label="Hourly demand baseline"><h2 className="admin-chart-card__title">Expected registrations by hour</h2><p>Average of recorded-day hourly counts. Fractional counts represent averages.</p><div className="analytics-hourly-scroll"><div className="analytics-hourly-bars">{data.hourly.map(h => <div className="analytics-hour" key={h.hour} title={`${String(h.hour).padStart(2,'0')}:00 — ${h.expected_registrations} expected registrations`}><span>{h.expected_registrations}</span><div className="analytics-hour-track"><div style={{height:`${h.expected_registrations / max * 100}%`}} /></div><small>{String(h.hour).padStart(2,'0')}</small></div>)}</div></div></section>}
      <section className="admin-analytics__table-section"><h2 className="admin-analytics__table-title">Service demand baseline</h2><div className="admin-analytics__table-wrapper"><table className="admin-analytics__table"><thead><tr><th>Service</th><th>Days with recorded activity</th><th>Expected registrations</th></tr></thead><tbody>{data.services.map(s => <tr key={s.service_id}><td>{s.service_name}</td><td>{s.recorded_days}</td><td>{s.expected_registrations ?? 'Unavailable'}</td></tr>)}</tbody></table></div>{!data.services.length && <p>No services configured.</p>}</section>
      <section className="admin-chart-card"><h2 className="admin-chart-card__title">Method and data coverage</h2><p>{data.method}</p><p>History: {data.window_start} through {data.window_end}. Latest activity: {data.latest_recorded_date || 'None'}. {data.days_without_records} calendar days have no registrations and are excluded. Today’s partial records are excluded.</p><ul>{data.limitations.map(note => <li key={note}>{note}</li>)}</ul></section>
    </>}
  </div>;
}
