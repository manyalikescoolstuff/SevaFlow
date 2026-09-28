import type { ReservationData, ServiceDefinition } from '../types/reservation';
import { GlassCard } from '../components/GlassCard';
import { CountdownTimer } from '../components/CountdownTimer';
import { useLanguage } from '../language';
interface Props {
  reservation: Pick<ReservationData, 'display_number' | 'expires_at'>; serviceDef: ServiceDefinition;
  onAccept: () => void; onReject: () => void; onExpired: () => void;
  busy?: boolean; serverOffset?: number;
}
export function WelcomePage({ reservation, serviceDef, onAccept, onReject, onExpired, busy, serverOffset }: Props) {
  const { t } = useLanguage();
  return <GlassCard>
    <div className="token-hero"><span>{t('Your token number', 'आपका टोकन नंबर')}</span>
      <div className="token-number">{reservation.display_number}</div>
      <span className="badge-pending">{t('Registration pending', 'पंजीकरण बाकी है')}</span>
    </div>
    <div className="content-stack">
      <section className="glass-subcard"><small>{t('Service', 'सेवा')}</small><h2>{serviceDef.label}</h2><p>{serviceDef.description}</p></section>
      <CountdownTimer expiresAt={reservation.expires_at} onExpired={onExpired} serverOffset={serverOffset} />
      <section className="glass-subcard"><h3>{t('Documents to bring', 'साथ लाने वाले दस्तावेज़')}</h3><ul className="document-list">{serviceDef.documentsChecklist.map(doc => <li key={doc}>{doc}</li>)}</ul></section>
      <button type="button" className="btn-kinetic-accept" onClick={onAccept} disabled={busy}>{t('Accept & continue', 'स्वीकार करें और आगे बढ़ें')} <span aria-hidden="true">→</span></button>
      <button type="button" className="btn-glass-reject" onClick={onReject} disabled={busy}>{t('Reject', 'अस्वीकार करें')}</button>
    </div>
  </GlassCard>;
}
