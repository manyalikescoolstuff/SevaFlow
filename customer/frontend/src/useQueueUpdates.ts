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
    const refresh = async () => {
      if (pending || cancelled) return;
      pending = true;
      setNextUpdate(null);
      try {
        const data = await load();
        if (!cancelled) { setTracking(data); setStale(false); }
      } catch {
        if (!cancelled) setStale(true);
      } finally {
        pending = false;
        if (!cancelled) {
          due = Date.now() + 60_000;
          setNextUpdate(due);
          setNow(Date.now());
        }
      }
    };
    const tick = () => {
      setNow(Date.now());
      if (Date.now() >= due) void refresh();
    };
    void refresh();
    const timer = window.setInterval(tick, 1000);
    document.addEventListener('visibilitychange', tick);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', tick);
    };
  }, [load]);
  return { tracking, stale, secondsRemaining: nextUpdate === null ? null : Math.max(0, Math.ceil((nextUpdate - now) / 1000)) };
}
