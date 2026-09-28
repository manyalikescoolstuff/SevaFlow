import { useState, type FormEvent } from 'react';
import { CountdownTimer } from '../components/CountdownTimer';
import { useLanguage } from '../language';
import type { Claim } from '../api';
interface Props {
  claim: Claim; serviceLabel: string; offset: number; busy: boolean;
  onBack: () => void; onExpired: () => void;
  onSubmit: (name: string, phone: string) => Promise<void>;
}
export function RegistrationPage({ claim, serviceLabel, offset, busy, onBack, onExpired, onSubmit }: Props) {
  const { t } = useLanguage();
  const draftKey = `sevaflow_draft:${claim.token_id}`;
  const [draft, setDraft] = useState<{ name: string; phone: string }>(() => {
    try { return JSON.parse(sessionStorage.getItem(draftKey) || 'null') || { name: '', phone: '' }; }
    catch { return { name: '', phone: '' }; }
  });
  const update = (key: 'name' | 'phone', value: string) => {
    const next = { ...draft, [key]: value }; setDraft(next);
    try { sessionStorage.setItem(draftKey, JSON.stringify(next)); } catch { /* form remains usable */ }
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    await onSubmit(draft.name.trim().replace(/\s+/g, ' '), draft.phone);
  };
  return <section className="glass-panel">
    <div className="token-hero"><span>{t('Your token number', 'आपका टोकन नंबर')}</span><div className="token-number">{claim.display_number}</div><span className="badge-pending">{t('Registration pending', 'पंजीकरण बाकी है')}</span><h2>{serviceLabel}</h2></div>
    <form className="content-stack" onSubmit={submit}>
      <div><h2>{t('Your details', 'आपकी जानकारी')}</h2><p>{t('Complete registration to join the waiting queue.', 'प्रतीक्षा कतार में शामिल होने के लिए पंजीकरण पूरा करें।')}</p></div>
      <CountdownTimer expiresAt={claim.reservation_expires_at} serverOffset={offset} onExpired={onExpired} />
      <label>{t('Full name', 'पूरा नाम')}<input required minLength={2} maxLength={120} name="name" autoComplete="name" value={draft.name} onChange={e => update('name', e.target.value)} placeholder={t('Enter your full name', 'अपना पूरा नाम लिखें')} disabled={busy} /></label>
      <label>{t('Mobile number', 'मोबाइल नंबर')}<span className="phone-field"><span>+91</span><input required type="tel" inputMode="numeric" pattern="[6-9][0-9]{9}" maxLength={10} name="phone" autoComplete="tel-national" value={draft.phone} onChange={e => update('phone', e.target.value.replace(/\D/g, ''))} placeholder={t('10-digit mobile number', '10 अंकों का मोबाइल नंबर')} disabled={busy} /></span></label>
      <p className="helper">{t('Your scan priority is saved.', 'आपकी स्कैन प्राथमिकता सुरक्षित है।')}</p>
      <button className="btn-kinetic-accept" disabled={busy} type="submit">{busy ? t('Confirming…', 'पुष्टि हो रही है…') : t('Confirm registration', 'पंजीकरण की पुष्टि करें')}</button>
      <button className="secondary-button" disabled={busy} type="button" onClick={onBack}>{t('Back', 'वापस')}</button>
    </form>
  </section>;
}
