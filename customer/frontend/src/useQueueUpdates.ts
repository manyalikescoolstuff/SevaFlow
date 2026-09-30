import { useEffect, useState } from 'react';
import type { Tracking } from './api';

export function useQueueUpdates(load: (() => Promise<Tracking>) | null) {
  const [tracking, setTracking] = useState<Tracking | null>(null);
  const [stale, setStale] = useState(false);
  const [nextUpdate, setNextUpdate] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    setTracking(null);
    setStale(false);
    setNextUpdate(null);
    if (!load) return;
    let cancelled = false;
    let pending = false;
    let due = 0;
    let failCount = 0;
    const refresh = async () => {
      if (pending || cancelled) return;
      pending = true;
      setNextUpdate(null);
      try {
        const data = await load();
        if (!cancelled) { setTracking(data); setStale(false); failCount = 0; }
      } catch {
        if (!cancelled) { setStale(true); failCount++; }
      } finally {
        pending = false;
        if (!cancelled) {
          if (failCount === 0) {
            due = Date.now() + 30_000;
          } else {
            due = Date.now() + Math.min(30_000, 2000 * Math.pow(2, failCount - 1));
          }
          setNextUpdate(due);
          setNow(Date.now());
        }
      }
    };
    const tick = () => {
      setNow(Date.now());
      if (Date.now() >= due) void refresh();
    };
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        due = 0;
        tick();
      }
    };
    const onOnline = () => {
      due = 0;
      tick();
    };
    void refresh();
    const timer = window.setInterval(tick, 1000);
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('online', onOnline);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('online', onOnline);
    };
  }, [load]);
  return { tracking, stale, secondsRemaining: nextUpdate === null ? null : Math.max(0, Math.ceil((nextUpdate - now) / 1000)) };
}
