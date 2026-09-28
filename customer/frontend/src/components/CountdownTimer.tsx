import { useEffect, useState } from 'react';
import { useLanguage } from '../language';
interface Props { expiresAt: string; onExpired?: () => void; serverOffset?: number }
export function CountdownTimer({ expiresAt, onExpired, serverOffset = 0 }: Props) {
  const { t } = useLanguage();
  const remaining = () => Math.max(0, Math.ceil((Date.parse(expiresAt) - Date.now() - serverOffset) / 1000));
  const [seconds, setSeconds] = useState(remaining);
  useEffect(() => {
    const tick = () => { const value = remaining(); setSeconds(value); if (value === 0) onExpired?.(); };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [expiresAt, serverOffset, onExpired]);
  return <div className={`registration-clock ${seconds <= 60 ? 'urgent' : ''}`}>
    <span>{t('Complete registration within', 'पंजीकरण पूरा करने का समय')}</span>
    <strong role="timer" aria-label={t('Registration time remaining', 'पंजीकरण के लिए शेष समय')}>{String(Math.floor(seconds / 60)).padStart(2, '0')}:{String(seconds % 60).padStart(2, '0')}</strong>
  </div>;
}
