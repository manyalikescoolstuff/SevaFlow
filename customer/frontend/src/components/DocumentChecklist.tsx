import React from 'react';

interface DocumentChecklistProps {
  documents: string[];
}

export const DocumentChecklist: React.FC<DocumentChecklistProps> = ({ documents }) => {
  return (
    <div className="checklist-container">
      <div className="checklist-header">
        <span className="checklist-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
          </svg>
          Suggested Documents
        </span>
        <span className="verification-notice">
          Pending Verification
        </span>
      </div>

      <div style={{
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
        marginBottom: '0.5rem',
        fontStyle: 'italic'
      }}>
        * Informational checklist only. No document uploads or mandatory checks required at this stage.
      </div>

      <ul className="doc-list">
        {documents.map((doc, idx) => (
          <li key={idx} className="doc-item">
            <span className="doc-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </span>
            <span>{doc}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};
