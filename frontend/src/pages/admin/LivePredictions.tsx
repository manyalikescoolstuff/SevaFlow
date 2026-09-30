import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
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
const mockHours = [0,0,0,0,0,0,0,0,4,10,18,24,20,12,16,18,14,8,0,0,0,0,0,0];
const mockForecast: Forecast = {
  forecast_date: 'Sample next day', timezone: 'Asia/Kolkata', generated_at: '', status: 'available', reason: null,
  method: 'Synthetic example for demonstrating the forecast layout. These figures are not calculated from real customers.',
  window_start: 'Sample day 1', window_end: 'Sample day 28', recorded_days: 14, required_days: 7,
  days_without_records: 14, latest_recorded_date: 'Sample day 28', registration_samples: 2016,
  expected_registrations: 144, historical_daily_min: 110, historical_daily_max: 182,
  hourly: mockHours.map((expected_registrations, hour) => ({ hour, expected_registrations })),
  services: [
    { service_id: 'mock-kyc', service_name: 'KYC', recorded_days: 14, expected_registrations: 54 },
    { service_id: 'mock-account', service_name: 'New account', recorded_days: 14, expected_registrations: 40 },
    { service_id: 'mock-cash', service_name: 'Cash transactions', recorded_days: 14, expected_registrations: 30 },
    { service_id: 'mock-help', service_name: 'Help desk', recorded_days: 14, expected_registrations: 20 },
  ],
  limitations: ['All figures on this view are mock data for UI demonstration.', 'No registrations, queue state, or real historical records are created.', 'Future wait remains unavailable; mock demand is not an operational recommendation.'],
};
export function LivePredictionsPage() {
  const [params] = useSearchParams();
  const preview = params.get('preview') === '1';
  const { session, logout } = useLiveAdmin();
  const [liveData, setData] = useState<Forecast | null>(null);
  const data = preview ? mockForecast : liveData;
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!session || preview) return;
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
  }, [session, logout, refresh, preview]);
  const max = Math.max(1, ...(data?.hourly.map(h => h.expected_registrations) || []));
  return <div className="admin-predictions">
    <header className="admin-predictions__header"><div><h1 className="admin-predictions__title">Predictions</h1><p>Next-day demand · {preview ? 'Mock data preview' : 'provisional recorded-day baseline'}</p></div><div className="analytics-date-controls"><Link to={preview ? '/admin/predictions' : '/admin/predictions?preview=1'}>{preview ? 'Use real data' : 'View mock data'}</Link>{!preview && <button onClick={() => setRefresh(n => n + 1)}>Refresh forecast</button>}</div></header>
    {preview && <p role="note" className="admin-demo-notice">Mock data preview — all figures below are synthetic. Real queue records are unchanged.</p>}
    {!preview && error && <p role="alert" className="admin-demo-notice">{error}{data && ' Showing the last successful forecast response.'}</p>}
    {!data ? <p role="status">{error ? 'Forecast unavailable. Retry with Refresh forecast.' : 'Checking recorded history…'}</p> : <>
      <p role="status">For {data.forecast_date} · {data.timezone} · {preview ? 'Static mock example' : error ? 'Update interrupted' : 'Refreshes every minute'}</p>
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
