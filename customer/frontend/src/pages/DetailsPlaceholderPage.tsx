import React from 'react';
import { ReservationData, ServiceDefinition } from '../types/reservation';
import { GlassCard } from '../components/GlassCard';

interface DetailsPlaceholderPageProps {
  reservation: ReservationData;
  serviceDef: ServiceDefinition;
  onBack: () => void;
}

export const DetailsPlaceholderPage: React.FC<DetailsPlaceholderPageProps> = ({
  reservation,
  serviceDef,
  onBack,
}) => {
  return (
    <GlassCard>
      <div style={{ padding: '1.75rem 1.25rem', textAlign: 'center' }}>
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: 'rgba(59, 130, 246, 0.15)',
          border: '1px solid rgba(59, 130, 246, 0.35)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1rem',
          color: '#60a5fa'
        }}>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
        </div>

        <div style={{
          display: 'inline-block',
          fontSize: '0.72rem',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: '#38bdf8',
          background: 'rgba(56, 189, 248, 0.1)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          padding: '0.2rem 0.65rem',
          borderRadius: '9999px',
          marginBottom: '0.75rem'
        }}>
          Stage 2 Placeholder • Scope Locked
        </div>

        <h2 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '1.4rem',
          fontWeight: 700,
          color: 'var(--text-pure)',
          marginBottom: '0.5rem'
        }}>
          Customer Details Placeholder
        </h2>

        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem', lineHeight: '1.5' }}>
          You have successfully accepted reservation for token <strong>{reservation.display_number}</strong>.
          Per Stage 1 scope, the customer registration form (Name & Mobile Number) will be connected in Stage 2.
        </p>

        {/* Preserved Context Summary */}
        <div className="glass-subcard" style={{ textAlign: 'left', marginBottom: '1.5rem' }}>
          <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '0.5rem' }}>
            Preserved Reservation Context:
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.82rem' }}>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Token: </span>
              <strong style={{ color: '#fff' }}>{reservation.display_number}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Status: </span>
              <span style={{ color: '#fbbf24', fontWeight: 600 }}>{reservation.status}</span>
            </div>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Service: </span>
              <span style={{ color: '#fff' }}>{serviceDef.label}</span>
            </div>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Session: </span>
              <span style={{ color: '#94a3b8', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                {reservation.claim_session_id || 'Active'}
              </span>
            </div>
          </div>
        </div>

        <button
          type="button"
          className="btn-glass-reject"
          onClick={onBack}
          style={{ width: '100%', borderColor: 'rgba(255,255,255,0.15)' }}
        >
          ← Back to Welcome Review
        </button>
      </div>
    </GlassCard>
  );
};
