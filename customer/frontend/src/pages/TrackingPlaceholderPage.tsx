import React from 'react';
import { ReservationData, ServiceDefinition } from '../types/reservation';
import { GlassCard } from '../components/GlassCard';

interface TrackingPlaceholderPageProps {
  reservation: ReservationData;
  serviceDef: ServiceDefinition;
}

export const TrackingPlaceholderPage: React.FC<TrackingPlaceholderPageProps> = ({
  reservation,
  serviceDef,
}) => {
  return (
    <GlassCard>
      <div style={{ padding: '2rem 1.25rem', textAlign: 'center' }}>
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid rgba(16, 185, 129, 0.35)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1rem',
          color: '#34d399'
        }}>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>

        <div style={{
          display: 'inline-block',
          fontSize: '0.72rem',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: '#34d399',
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          padding: '0.2rem 0.65rem',
          borderRadius: '9999px',
          marginBottom: '0.75rem'
        }}>
          Already Registered • Active in Queue
        </div>

        <div className="token-number" style={{ fontSize: '3rem', margin: '0.5rem 0' }}>
          {reservation.display_number}
        </div>

        <h2 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '1.25rem',
          fontWeight: 700,
          color: 'var(--text-pure)',
          marginBottom: '0.35rem'
        }}>
          {serviceDef.label}
        </h2>

        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          Registration controls are locked because this token has already been validated and is currently waiting in line.
        </p>

        <div className="glass-subcard" style={{ textAlign: 'left', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Queue Status:</span>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#38bdf8' }}>WAITING</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Scan Sequence:</span>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fff' }}>#{reservation.scan_sequence || 14}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Approx. Ahead:</span>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f59e0b' }}>
              {reservation.queue_position !== undefined ? `${reservation.queue_position} citizen(s)` : '2 citizens ahead'}
            </span>
          </div>
        </div>

        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Live queue tracking and audio/visual call notifications will be connected in Stage 3.
        </div>
      </div>
    </GlassCard>
  );
};
