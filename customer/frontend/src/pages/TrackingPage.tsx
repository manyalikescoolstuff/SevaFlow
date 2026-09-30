import type { Claim, Tracking } from '../api';
import { useLanguage } from '../language';
export function TrackingPage({ claim, tracking, serviceLabel, stale, secondsRemaining, preview = false }: { claim: Pick<Claim, 'display_number' | 'status'>; tracking: Tracking | null; serviceLabel: string; stale: boolean; secondsRemaining: number | null; preview?: boolean }) {
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
      {preview && <p className="helper">{t('Preview · sample queue data', 'पूर्वावलोकन · नमूना कतार डेटा')}</p>}
      {status === 'WAITING' && <h2>{t('Your turn is on its way', 'आपकी बारी आने वाली है')}</h2>}
      {status === 'WAITING' && <section className="glass-subcard"><div className="tracking-metrics">
        <div><strong>{tracking?.estimated_wait_minutes ?? '—'}{tracking?.estimated_wait_minutes != null && <small> {t('min', 'मिनट')}</small>}</strong><span>{t('Estimated wait', 'अनुमानित प्रतीक्षा')}</span><small>{t('Approximate', 'अनुमान')}</small></div>
        <div><strong>{tracking?.people_ahead ?? '—'}</strong><span>{t('People ahead', 'आपसे आगे लोग')}</span></div>
      </div><p className="tracking-freshness">{stale ? t('Connection interrupted — showing last update', 'कनेक्शन बाधित — पिछली जानकारी दिखाई जा रही है') : tracking ? `${t('Last updated', 'पिछला अपडेट')} ${new Date(tracking.server_time).toLocaleTimeString()}` : t('Loading queue status…', 'कतार की जानकारी लोड हो रही है…')}</p></section>}
      <section className="glass-subcard" style={{ textAlign: 'center' }}>
        <p>{secondsRemaining === null ? t('Updating queue status…', 'कतार अपडेट हो रही है…') : stale ? t('Retrying in', 'पुनः प्रयास में') : t('Next update in', 'अगला अपडेट')}</p>
        <strong style={{ fontSize: '2rem', color: '#087db8', fontVariantNumeric: 'tabular-nums' }}>
          {secondsRemaining === null ? '…' : `${Math.floor(secondsRemaining / 60).toString().padStart(2, '0')}:${(secondsRemaining % 60).toString().padStart(2, '0')}`}
        </strong>
        <p className="helper">{t('Automatically refreshes every minute.', 'हर मिनट अपने आप अपडेट होता है।')}</p>
      </section>
      <div className="glass-subcard">{tracking?.counter_label ? <><small>{t('Your counter', 'आपका काउंटर')}</small><h2>{tracking.counter_label}</h2></> : <p>{status === 'WAITING' ? t('We’ll show your counter here when you are called.', 'बुलाए जाने पर आपका काउंटर यहाँ दिखेगा।') : labels[status]}</p>}</div>
      {status === 'WAITING' && <p className="helper">{t('Wait times may change as services finish or customers are recalled.', 'सेवा पूरी होने या ग्राहकों को दोबारा बुलाने पर प्रतीक्षा समय बदल सकता है।')}</p>}
      {stale && status !== 'WAITING' && <p role="status">{t('Connection interrupted. Retrying automatically.', 'कनेक्शन बाधित है। अपने आप पुनः प्रयास हो रहा है।')}</p>}
    </div>
  </section>;
}
