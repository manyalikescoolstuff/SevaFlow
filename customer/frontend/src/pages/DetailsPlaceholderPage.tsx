import React, { useState } from 'react';
import { ReservationData, ServiceDefinition } from '../types/reservation';
import { GlassCard } from '../components/GlassCard';

interface DetailsPlaceholderPageProps {
  reservation: ReservationData;
  serviceDef: ServiceDefinition;
  onBack: () => void;
  onRegistered: () => void;
}

export const DetailsPlaceholderPage: React.FC<DetailsPlaceholderPageProps> = ({
  reservation,
  serviceDef,
  onBack,
  onRegistered,
}) => {
  const [details, setDetails] = useState({ name: '', phone: '', email: '' });
  const [submitted, setSubmitted] = useState(false);

  const update = (field: keyof typeof details, value: string) => {
    setDetails((current) => ({ ...current, [field]: value }));
    setSubmitted(false);
  };

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
          Stage 2 Preview • Mock data
        </div>

        <h2 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '1.4rem',
          fontWeight: 700,
          color: 'var(--text-pure)',
          marginBottom: '0.5rem'
        }}>
          Join the waiting queue
        </h2>

        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem', lineHeight: '1.5' }}>
          Complete registration for token <strong>{reservation.display_number}</strong>. This preview mirrors the
          customer form; the live QR flow sends these details to the backend.
        </p>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            setSubmitted(true);
            onRegistered();
          }}
          style={{ textAlign: 'left', marginBottom: '1.25rem' }}
        >
          {([
            ['name', 'Full name', 'Enter your full name', 'text'],
            ['phone', 'Mobile number', '10-digit mobile number', 'tel'],
            ['email', 'Email address', 'you@example.com', 'email'],
          ] as const).map(([field, label, placeholder, type]) => (
            <label key={field} style={{ display: 'block', marginBottom: '0.8rem', color: 'var(--text-pure)', fontSize: '0.82rem', fontWeight: 600 }}>
              {label}
              <input
                required
                type={type}
                value={details[field]}
                onChange={(event) => update(field, event.target.value)}
                placeholder={placeholder}
                style={{ width: '100%', marginTop: '0.35rem', padding: '0.75rem 0.8rem', borderRadius: '0.7rem', border: '1px solid rgba(148,163,184,0.35)', background: 'rgba(255,255,255,0.08)', color: 'var(--text-pure)', boxSizing: 'border-box' }}
              />
            </label>
          ))}
          {submitted && (
            <p role="status" style={{ color: '#34d399', fontSize: '0.8rem', margin: '0 0 0.8rem' }}>
              Preview registration captured. The live flow will now request a queue token.
            </p>
          )}
          <button type="submit" className="btn-glass-primary" style={{ width: '100%' }}>
            {submitted ? 'Registration captured' : 'Confirm registration'}
          </button>
        </form>

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
