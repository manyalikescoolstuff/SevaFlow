import React, { useState } from 'react';
import { MockPreviewState } from '../types/reservation';

interface DevStateSwitcherProps {
  currentCategory: string | null;
  currentQNo: string | null;
  activePreviewState: MockPreviewState | null;
  onSelectPreviewState: (state: MockPreviewState | null) => void;
  onNavigateDemoUrl: (cat: string, qNo: string) => void;
  onResetData: () => void;
}

export const DevStateSwitcher: React.FC<DevStateSwitcherProps> = ({
  currentCategory,
  currentQNo,
  activePreviewState,
  onSelectPreviewState,
  onNavigateDemoUrl,
  onResetData,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const previewStates: { label: string; value: MockPreviewState | null }[] = [
    { label: 'Normal (Valid)', value: null },
    { label: 'Loading', value: 'loading' },
    { label: 'Expired', value: 'expired' },
    { label: 'Mismatch / Unknown', value: 'invalid_mismatched' },
    { label: 'Claimed by Other', value: 'claimed_other' },
    { label: 'Already Registered', value: 'already_registered' },
    { label: 'Rejected', value: 'rejected' },
    { label: 'Connection Error', value: 'connection_error' },
  ];

  const demoPresets = [
    { label: 'Aadhaar (A024)', cat: 'aadhar', qNo: 'A024' },
    { label: 'KYC (K012)', cat: 'kyc', qNo: 'K012' },
    { label: 'Bank Acc (B008)', cat: 'new_account', qNo: 'B008' },
    { label: 'Cash (C045)', cat: 'cash', qNo: 'C045' },
    { label: 'Help Desk (H003)', cat: 'helpdesk', qNo: 'H003' },
    { label: 'Missing Query', cat: '', qNo: '' },
    { label: 'Unknown Cat', cat: 'passport', qNo: 'P999' },
  ];

  return (
    <div className="dev-switcher">
      <div 
        className="dev-switcher-header" 
        onClick={() => setIsOpen(!isOpen)}
        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{
            display: 'inline-block',
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: activePreviewState ? '#f59e0b' : '#10b981',
          }} />
          <span>Stage 1 Dev Preview Controller {activePreviewState ? `[Override: ${activePreviewState}]` : '[Normal]'}</span>
        </div>
        <button 
          type="button" 
          style={{ 
            background: 'none', 
            border: 'none', 
            color: '#38bdf8', 
            fontSize: '0.75rem', 
            cursor: 'pointer',
            padding: '2px 6px',
            borderRadius: '4px'
          }}
        >
          {isOpen ? '▼ Collapse' : '▲ Expand Controls'}
        </button>
      </div>

      {isOpen && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', paddingTop: '0.25rem' }}>
          {/* Quick preset URLs */}
          <div>
            <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
              Switch Mock QR Entry URL (Preserves qNo & cat query parameters):
            </div>
            <div className="dev-switcher-controls">
              {demoPresets.map((preset, idx) => {
                const isActive = currentCategory === preset.cat && currentQNo === preset.qNo;
                return (
                  <button
                    key={idx}
                    type="button"
                    className={`dev-btn ${isActive ? 'active' : ''}`}
                    onClick={() => onNavigateDemoUrl(preset.cat, preset.qNo)}
                  >
                    {preset.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Mock State Overrides */}
          <div>
            <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
              Simulate Stage 1 States:
            </div>
            <div className="dev-switcher-controls">
              {previewStates.map((st, idx) => {
                const isSelected = activePreviewState === st.value;
                return (
                  <button
                    key={idx}
                    type="button"
                    className={`dev-btn ${isSelected ? 'active' : ''}`}
                    style={isSelected ? { backgroundColor: '#3b82f6', color: '#fff', borderColor: '#60a5fa' } : {}}
                    onClick={() => onSelectPreviewState(st.value)}
                  >
                    {st.label}
                  </button>
                );
              })}

              <button
                type="button"
                className="dev-btn"
                style={{ marginLeft: 'auto', backgroundColor: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5', borderColor: 'rgba(239, 68, 68, 0.4)' }}
                onClick={onResetData}
                title="Reset all mock deadlines to fresh 5-minute windows"
              >
                🔄 Reset 5-min Deadlines
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
