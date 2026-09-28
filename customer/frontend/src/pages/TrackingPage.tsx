import type { Claim, Tracking } from '../api';
import { useLanguage } from '../language';
export function TrackingPage({ claim, tracking, serviceLabel, stale }: { claim: Claim; tracking: Tracking | null; serviceLabel: string; stale: boolean }) {
  const { t } = useLanguage();
  const status = tracking?.status || claim.status;
  const labels: Record<string, string> = {
    WAITING: t('Waiting', 'प्रतीक्षा में'), CALLED: t('Please go to your counter', 'कृपया अपने काउंटर पर जाएँ'),
    SERVING: t('Service in progress', 'सेवा जारी है'), COMPLETED: t('Service completed', 'सेवा पूरी हुई'),
    MISSED: t('Missed turn — awaiting recall', 'बारी छूट गई — दोबारा बुलाने की प्रतीक्षा'),
    CLOSED_MISSED: t('Token closed — please request a new token', 'टोकन बंद — कृपया नया टोकन लें'),
  };
  return <section className="glass-panel">
    <div className="token-hero"><span>{t('Your token number', 'आपका टोकन नंबर')}</span><div className="token-number">{claim.display_number}</div><span className="status-badge" role="status">{labels[status] || status}</span><h2>{serviceLabel}</h2></div>
    <div className="content-stack">
      {status === 'WAITING' && <section className="glass-subcard"><div className="tracking-metrics">
        <div><strong>{tracking?.estimated_wait_minutes ?? '—'}{tracking?.estimated_wait_minutes != null && <small> {t('min', 'मिनट')}</small>}</strong><span>{t('Estimated wait', 'अनुमानित प्रतीक्षा')}</span><small>{t('Approximate', 'अनुमान')}</small></div>
        <div><strong>{tracking?.people_ahead ?? '—'}</strong><span>{t('People ahead', 'आपसे आगे लोग')}</span></div>
      </div><p className="tracking-freshness">{stale ? t('Connection interrupted — showing last update', 'कनेक्शन बाधित — पिछली जानकारी दिखाई जा रही है') : tracking ? t('Live · updated just now', 'लाइव · अभी अपडेट हुआ') : t('Loading queue status…', 'कतार की जानकारी लोड हो रही है…')}</p></section>}
      <div className="glass-subcard">{tracking?.counter_label ? <><small>{t('Your counter', 'आपका काउंटर')}</small><h2>{tracking.counter_label}</h2></> : <p>{status === 'WAITING' ? t('We’ll show your counter here when you are called.', 'बुलाए जाने पर आपका काउंटर यहाँ दिखेगा।') : labels[status]}</p>}</div>
      {status === 'WAITING' && <p className="helper">{t('Wait times may change as services finish or customers are recalled.', 'सेवा पूरी होने या ग्राहकों को दोबारा बुलाने पर प्रतीक्षा समय बदल सकता है।')}</p>}
      {stale && status !== 'WAITING' && <p role="status">{t('Connection interrupted. Retrying automatically.', 'कनेक्शन बाधित है। अपने आप पुनः प्रयास हो रहा है।')}</p>}
    </div>
  </section>;
}
