import { useCallback, useEffect, useRef, useState } from 'react';
import { Header } from './components/Header';
import { WelcomePage } from './pages/WelcomePage';
import { RegistrationPage } from './pages/RegistrationPage';
import { TrackingPage } from './pages/TrackingPage';
import { MockApp } from './MockApp';
import { getServiceDefinition } from './config/services';
import { localizeService } from './config/serviceTranslations';
import { useLanguage } from './language';
import { api, ApiError, hash, newCredential, ownership, type BrowserClaim, type Claim, type Tracking } from './api';

function CustomerApp() {
  const { t, language } = useLanguage();
  const [url, setUrl] = useState(() => new URL(location.href));
  const [claim, setClaim] = useState<Claim | null>(null);
  const [tracking, setTracking] = useState<Tracking | null>(null);
  const [stale, setStale] = useState(false);
  const [view, setView] = useState<'welcome' | 'details'>('welcome');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [expired, setExpired] = useState(false);
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const saved = useRef<BrowserClaim | null>(null);
  const storageKey = useRef('');
  const operation = useRef(false);
  const service = getServiceDefinition(url.searchParams.get('cat'));
  const number = url.searchParams.get('qNo')?.trim().toUpperCase();
  useEffect(() => {
    const navigate = () => setUrl(new URL(location.href));
    window.addEventListener('popstate', navigate);
    return () => window.removeEventListener('popstate', navigate);
  }, []);
  const persist = (value: BrowserClaim) => {
    localStorage.setItem(storageKey.current, JSON.stringify(value));
    saved.current = value;
  };
  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError(null); setClaim(null); setTracking(null); setExpired(false);
    const initialize = async () => {
      if (!service || !number) throw new ApiError(400, 'Scan a valid kiosk QR code with a service and token number.');
      const reservation = url.searchParams.get('reservation');
      if (!reservation) throw new ApiError(400, 'This QR is missing its reservation credential. Please scan the QR issued by the kiosk.');
      const key = `sevaflow_claim:${reservation}`;
      storageKey.current = key;
      const raw = localStorage.getItem(key);
      // Synchronous persistence before the first await is important for StrictMode
      // and reload recovery after a lost claim response.
      const stored: BrowserClaim = raw ? JSON.parse(raw) : { session: newCredential(), recovery: newCredential(), tracking: newCredential() };
      if (!stored.session || !stored.recovery || !stored.tracking) throw new Error('Saved browser credentials are unavailable. Use the original browser.');
      localStorage.setItem(key, JSON.stringify(stored));
      const secret = new URLSearchParams(url.hash.slice(1)).get('claim');
      if (secret) {
        stored.claimHash = await hash(secret);
        localStorage.setItem(key, JSON.stringify(stored));
        const clean = new URL(location.href); clean.hash = '';
        history.replaceState(null, '', clean);
      }
      const recoveryHash = await hash(stored.recovery);
      const data = stored.tokenId ? await api<Claim>('/recover', {
        token_id: stored.tokenId, claim_session_id: stored.session, recovery_credential_hash: recoveryHash,
      }) : await api<Claim>('/claim', {
        hardware_reservation_id: reservation, claim_secret_hash: stored.claimHash || '',
        browser_session_id: stored.session, recovery_credential_hash: recoveryHash,
        service_id: service.backendServiceId, display_number: number,
      });
      if (cancelled) return;
      if (data.service_id !== service.backendServiceId || data.display_number !== number) throw new ApiError(400, 'QR service or token number does not match this reservation.');
      // Merge stored UI choices in case another mount completed during this request.
      const latest = JSON.parse(localStorage.getItem(key) || '{}') as BrowserClaim;
      persist({ ...stored, ...latest, tokenId: data.token_id });
      setOffset(Date.parse(data.server_time) - Date.now());
      setClaim(data); setView(latest.accepted ? 'details' : 'welcome');
    };
    initialize().catch(e => { if (!cancelled) setError(e instanceof Error ? e : new Error('Unable to open token')); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [url, attempt]);
  useEffect(() => {
    if (!claim?.registered_at) return;
    let cancelled = false;
    let timer: number;
    const poll = async () => {
      try {
        const data = await api<Tracking>(`/token/${claim.token_id}/status`, undefined, await hash(saved.current!.tracking));
        if (!cancelled) { setTracking(data); setStale(false); }
      } catch { if (!cancelled) setStale(true); }
      if (!cancelled) timer = window.setTimeout(poll, 4000);
    };
    void poll();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [claim?.token_id, claim?.registered_at]);
  const onExpired = useCallback(() => setExpired(true), []);
  const run = async (action: () => Promise<void>) => {
    if (operation.current) return;
    operation.current = true; setBusy(true); setError(null);
    try { await action(); }
    catch (e) { setError(e instanceof Error ? e : new Error('Request failed')); if (e instanceof ApiError && e.status === 410) setExpired(true); }
    finally { operation.current = false; setBusy(false); }
  };
  const register = async (name: string, phone: string, email: string) => run(async () => {
    const credentials = saved.current!;
    await api('/register', { ...await ownership(credentials), tracking_secret_hash: await hash(credentials.tracking), customer_name: name, phone_number: phone, email });
    const data = await api<Claim>('/recover', await ownership(credentials));
    setClaim(data); setExpired(false);
    sessionStorage.removeItem(`sevaflow_draft:${data.token_id}`);
  });
  const reject = () => void run(async () => setClaim(await api<Claim>('/reject', await ownership(saved.current!))));
  const accept = () => {
    if (!claim || Date.parse(claim.reservation_expires_at) <= Date.now() + offset) { setExpired(true); return; }
    try { persist({ ...saved.current!, accepted: true }); setView('details'); }
    catch (e) { setError(e as Error); }
  };
  const localizedService = service ? localizeService(service, language) : null;
  const serviceLabel = localizedService?.label || '';
  const errorText = error instanceof ApiError && error.status === 0 ? t('Connection interrupted. Retry to recover your saved token.', 'कनेक्शन बाधित है। सुरक्षित टोकन पुनः पाने के लिए प्रयास करें।')
    : language === 'hi' ? t('', 'टोकन नहीं खोला जा सका। सही कियोस्क QR और मूल ब्राउज़र का उपयोग करें।') : error?.message;
  return <main className="portal-wrapper"><Header />
    {error && <div className="error-notice" role="alert"><p>{errorText}</p>{!busy && <button className="secondary-button" onClick={() => setAttempt(n => n + 1)}>{t('Retry / recover token', 'पुनः प्रयास / टोकन वापस पाएँ')}</button>}</div>}
    {loading ? <section className="glass-panel message-card" role="status">{t('Verifying your reservation…', 'आपके आरक्षण की जाँच हो रही है…')}</section>
      : claim?.registered_at ? <TrackingPage claim={claim} tracking={tracking} stale={stale} serviceLabel={serviceLabel} />
      : claim?.status === 'CANCELLED' ? <section className="glass-panel message-card"><h2>{t('Reservation declined', 'आरक्षण अस्वीकार किया गया')}</h2><p>{t('You can request a new token at the kiosk.', 'आप कियोस्क से नया टोकन ले सकते हैं।')}</p></section>
      : expired || claim?.status === 'EXPIRED' ? <section className="glass-panel message-card"><h2>{t('Registration window ended', 'पंजीकरण का समय समाप्त')}</h2><p>{t('Request a new token at the kiosk. If you just submitted your details, recover your token to check the result.', 'कियोस्क से नया टोकन लें। यदि आपने अभी जानकारी भेजी है, तो परिणाम देखने के लिए टोकन वापस पाएँ।')}</p><button className="secondary-button" onClick={() => setAttempt(n => n + 1)}>{t('Recover token', 'टोकन वापस पाएँ')}</button></section>
      : claim && localizedService && view === 'details' ? <RegistrationPage claim={claim} serviceLabel={serviceLabel} offset={offset} busy={busy} onBack={() => { persist({ ...saved.current!, accepted: false }); setView('welcome'); }} onExpired={onExpired} onSubmit={register} />
      : claim && localizedService ? <WelcomePage reservation={{ display_number: claim.display_number, expires_at: claim.reservation_expires_at }} serviceDef={localizedService} busy={busy} serverOffset={offset} onAccept={accept} onReject={reject} onExpired={onExpired} /> : null}
  </main>;
}
export function App() {
  return import.meta.env.DEV && new URLSearchParams(location.search).get('preview') === '1' ? <MockApp /> : <CustomerApp />;
}
