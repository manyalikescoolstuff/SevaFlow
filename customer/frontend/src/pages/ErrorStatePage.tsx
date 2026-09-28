import React from 'react';
import { GlassCard } from '../components/GlassCard';

interface ErrorStatePageProps {
  errorCode?: string;
  errorMessage?: string;
  onRetry?: () => void;
  onNavigateDemo?: (cat: string, qNo: string) => void;
}

export const ErrorStatePage: React.FC<ErrorStatePageProps> = ({
  errorCode = 'UNKNOWN_ERROR',
  errorMessage = 'An unexpected error occurred while validating your token reservation.',
  onRetry,
  onNavigateDemo,
}) => {
  const getErrorIcon = () => {
    switch (errorCode) {
      case 'NETWORK_ERROR':
        return (
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="1" y1="1" x2="23" y2="23"></line>
            <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"></path>
            <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"></path>
            <path d="M10.71 5.05A16 16 0 0 1 22.58 9"></path>
            <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"></path>
            <path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path>
            <line x1="12" y1="20" x2="12.01" y2="20"></line>
          </svg>
        );
      case 'EXPIRED':
        return (
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 14 14"></polyline>
          </svg>
        );
      default:
        return (
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fb7185" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        );
    }
  };

  const getErrorTitle = () => {
    switch (errorCode) {
      case 'MISSING_PARAMS': return 'Incomplete QR Code';
      case 'UNSUPPORTED_CATEGORY': return 'Unsupported Service';
      case 'MISMATCHED_RESERVATION': return 'Reservation Not Found';
      case 'EXPIRED': return 'Registration Expired';
      case 'CLAIMED_BY_ANOTHER': return 'Session Conflict';
      case 'NETWORK_ERROR': return 'Connection Error';
      default: return 'Token Validation Issue';
    }
  };

  return (
    <GlassCard>
      <div style={{ padding: '2rem 1.25rem', textAlign: 'center' }}>
        <div style={{
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          backgroundColor: 'rgba(255, 255, 255, 0.05)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1.25rem',
        }}>
          {getErrorIcon()}
        </div>

        <div style={{
          display: 'inline-block',
          fontSize: '0.7rem',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: '#fb7185',
          background: 'rgba(244, 63, 94, 0.1)',
          border: '1px solid rgba(244, 63, 94, 0.25)',
          padding: '0.2rem 0.65rem',
          borderRadius: '9999px',
          marginBottom: '0.75rem'
        }}>
          Error Code: {errorCode}
        </div>

        <h2 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '1.4rem',
          fontWeight: 700,
          color: 'var(--text-pure)',
          marginBottom: '0.5rem'
        }}>
          {getErrorTitle()}
        </h2>

        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1.5rem', lineHeight: '1.5' }}>
          {errorMessage}
        </p>

        {onRetry && (
          <button
            type="button"
            className="btn-kinetic-accept"
            onClick={onRetry}
            style={{ marginBottom: '0.75rem' }}
          >
            <span>🔄 Retry Connection</span>
          </button>
        )}

        {onNavigateDemo && (
          <div style={{ marginTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '1rem' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              Or load valid demo reservation:
            </div>
            <button
              type="button"
              className="btn-glass-reject"
              onClick={() => onNavigateDemo('aadhar', 'A024')}
            >
              Load Standard Aadhaar (A024)
            </button>
          </div>
        )}
      </div>
    </GlassCard>
  );
};
