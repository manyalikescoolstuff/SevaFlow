import React from 'react';
import { ReservationData } from '../types/reservation';
import { GlassCard } from '../components/GlassCard';

interface RejectedPageProps {
  reservation: ReservationData;
  onReconsider: () => void;
}

export const RejectedPage: React.FC<RejectedPageProps> = ({ reservation, onReconsider }) => {
  return (
    <GlassCard>
      <div style={{ padding: '2rem 1.25rem', textAlign: 'center' }}>
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: 'rgba(244, 63, 94, 0.15)',
          border: '1px solid rgba(244, 63, 94, 0.35)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1.25rem',
          color: '#fb7185'
        }}>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </div>

        <h2 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '1.4rem',
          fontWeight: 700,
          color: 'var(--text-pure)',
          marginBottom: '0.5rem'
        }}>
          Token Destroyed
        </h2>

        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.5rem', lineHeight: '1.5' }}>
          Your token <strong>{reservation.display_number}</strong> has been cancelled.
        </p>

        <div className="glass-subcard" style={{ textAlign: 'left', marginBottom: '1.5rem' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            If you need assistance or wish to receive a new token, please touch the button on the physical kiosk dispenser.
          </div>
        </div>

        <button
          type="button"
          className="btn-glass-reject"
          onClick={() => { window.location.href = '/'; }}
          style={{ width: '100%', borderColor: 'rgba(255,255,255,0.15)', marginBottom: '0.5rem' }}
        >
          Return to Home
        </button>
        <button
          type="button"
          className="secondary-button"
          onClick={onReconsider}
          style={{ width: '100%' }}
        >
          🔄 Re-open Welcome Page (Demo)
        </button>
      </div>
    </GlassCard>
  );
};
