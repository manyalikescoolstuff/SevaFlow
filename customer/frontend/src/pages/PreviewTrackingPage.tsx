import { useCallback } from 'react';
import { useQueueUpdates } from '../useQueueUpdates';
import { TrackingPage } from './TrackingPage';

export function PreviewTrackingPage({ number, serviceLabel }: { number: string; serviceLabel: string }) {
  const load = useCallback(async () => ({
    status: 'WAITING', people_ahead: 3, estimated_wait_minutes: 12,
    counter_label: null, server_time: new Date().toISOString(), recall_attempts: 0,
  }), []);
  const updates = useQueueUpdates(load);
  return <TrackingPage claim={{ display_number: number, status: 'WAITING' }} serviceLabel={serviceLabel} {...updates} preview />;
}
