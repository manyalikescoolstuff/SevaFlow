import React, { useEffect, useState, useCallback } from 'react';
import { 
  ClaimValidationResult, 
  MockPreviewState 
} from './types/reservation';
import { getServiceDefinition } from './config/services';
import { 
  getDevPreviewState, 
  mockAcceptReservation, 
  mockRejectReservation, 
  resetMockData, 
  setDevPreviewState, 
  validateClaimRequest 
} from './mock/mockAdapter';

import { Header } from './components/Header';
import { WelcomePage } from './pages/WelcomePage';
import { DetailsPlaceholderPage } from './pages/DetailsPlaceholderPage';
import { RejectedPage } from './pages/RejectedPage';
import { TrackingPlaceholderPage } from './pages/TrackingPlaceholderPage';
import { ErrorStatePage } from './pages/ErrorStatePage';
import { DevStateSwitcher } from './components/DevStateSwitcher';

type ViewMode = 'WELCOME' | 'DETAILS_PLACEHOLDER' | 'REJECTED';

export const MockApp: React.FC = () => {
  // Query parameters state
  const [catParam, setCatParam] = useState<string | null>(null);
  const [qNoParam, setQNoParam] = useState<string | null>(null);

  // Validation & Data state
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [validationResult, setValidationResult] = useState<ClaimValidationResult | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('WELCOME');

  // Dev preview override state
  const [activePreviewOverride, setActivePreviewOverride] = useState<MockPreviewState | null>(() => getDevPreviewState());

  // Parse window.location query params
  const parseCurrentUrl = useCallback(() => {
    const url = new URL(window.location.href);
    const cat = url.searchParams.get('cat');
    const qNo = url.searchParams.get('qNo');

    // Default demo routing if visiting root "/" without query
    if (!cat && !qNo && (url.pathname === '/' || url.pathname === '')) {
      // Set canonical demo url: /qr?cat=aadhar&qNo=A024
      url.pathname = '/qr';
      url.searchParams.set('cat', 'aadhar');
      url.searchParams.set('qNo', 'A024');
      window.history.replaceState({}, '', url.toString());
      setCatParam('aadhar');
      setQNoParam('A024');
      return { cat: 'aadhar', qNo: 'A024' };
    }

    setCatParam(cat);
    setQNoParam(qNo);
    return { cat, qNo };
  }, []);

  // Run validation
  const executeValidation = useCallback(async (
    cat: string | null, 
    qNo: string | null, 
    override?: MockPreviewState | null
  ) => {
    setIsLoading(true);
    const result = await validateClaimRequest(cat, qNo, override);
    setValidationResult(result);
    setIsLoading(false);

    // If reservation is already rejected in storage
    if (result.reservation?.status === 'REJECTED') {
      setViewMode('REJECTED');
    } else {
      setViewMode('WELCOME');
    }
  }, []);

  // Initialize on mount and on popstate
  useEffect(() => {
    const { cat, qNo } = parseCurrentUrl();
    executeValidation(cat, qNo, activePreviewOverride);

    const handlePopState = () => {
      const parsed = parseCurrentUrl();
      executeValidation(parsed.cat, parsed.qNo, activePreviewOverride);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [parseCurrentUrl, executeValidation, activePreviewOverride]);

  // Handle URL change from Dev Switcher
  const handleNavigateDemoUrl = (newCat: string, newQNo: string) => {
    const url = new URL(window.location.href);
    url.pathname = '/qr';
    url.searchParams.delete('cat');
    url.searchParams.delete('qNo');

    if (newCat) url.searchParams.set('cat', newCat);
    if (newQNo) url.searchParams.set('qNo', newQNo);

    window.history.pushState({}, '', url.toString());
    setCatParam(newCat || null);
    setQNoParam(newQNo || null);
    executeValidation(newCat || null, newQNo || null, activePreviewOverride);
  };

  // Handle Dev Preview State change
  const handleSelectPreviewState = (state: MockPreviewState | null) => {
    setActivePreviewOverride(state);
    setDevPreviewState(state);
    executeValidation(catParam, qNoParam, state);
  };

  // Reset Mock Data
  const handleResetData = () => {
    resetMockData();
    setActivePreviewOverride(null);
    setDevPreviewState(null);
    executeValidation(catParam, qNoParam, null);
  };

  // Handle Accept
  const handleAccept = () => {
    if (!validationResult?.reservation) return;
    const updated = mockAcceptReservation(validationResult.reservation.token_id);
    if (updated) {
      setValidationResult(prev => prev ? { ...prev, reservation: updated } : null);
      setViewMode('DETAILS_PLACEHOLDER');
    }
  };

  // Handle Reject
  const handleReject = () => {
    if (!validationResult?.reservation) return;
    const updated = mockRejectReservation(validationResult.reservation.token_id);
    if (updated) {
      setValidationResult(prev => prev ? { ...prev, reservation: updated } : null);
      setViewMode('REJECTED');
    }
  };

  // Handle Expiry
  const handleExpired = () => {
    if (validationResult?.reservation) {
      setValidationResult({
        success: false,
        errorCode: 'EXPIRED',
        errorMessage: 'Registration deadline has expired. Please touch the kiosk to request a new token.',
        reservation: {
          ...validationResult.reservation,
          status: 'EXPIRED',
        },
      });
    }
  };

  // Retry Connection Error
  const handleRetry = () => {
    executeValidation(catParam, qNoParam, activePreviewOverride);
  };

  // Render Page Content based on state
  const renderContent = () => {
    // 1. Loading State
    if (isLoading || activePreviewOverride === 'loading') {
      return (
        <div className="glass-panel" style={{ padding: '3.5rem 1.5rem', textAlign: 'center' }}>
          <div style={{
            width: '48px',
            height: '48px',
            border: '3px solid rgba(56, 189, 248, 0.2)',
            borderTopColor: '#38bdf8',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
            margin: '0 auto 1.25rem'
          }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: '#fff', marginBottom: '0.35rem' }}>
            Validating Token...
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Verifying reservation with SevaFlow kiosk services.
          </p>
        </div>
      );
    }

    // 2. Validation Failed (Error / Mismatch / Expired / Session Conflict / Network Error)
    if (!validationResult || !validationResult.success) {
      return (
        <ErrorStatePage
          errorCode={validationResult?.errorCode}
          errorMessage={validationResult?.errorMessage}
          onRetry={validationResult?.errorCode === 'NETWORK_ERROR' ? handleRetry : undefined}
          onNavigateDemo={handleNavigateDemoUrl}
        />
      );
    }

    const reservation = validationResult.reservation!;
    const serviceDef = getServiceDefinition(reservation.category) || {
      key: reservation.category,
      label: 'Service',
      backendServiceId: reservation.service_id,
      buttonLabel: 'Counter Service',
      isProvisional: true,
      description: 'Citizen counter service',
      documentsChecklist: ['Standard Government Identity Proof'],
    };

    // 3. Already Registered State
    if (reservation.is_registered || reservation.status === 'WAITING') {
      return (
        <TrackingPlaceholderPage
          reservation={reservation}
          serviceDef={serviceDef}
        />
      );
    }

    // 4. View Mode: Rejected Confirmation
    if (viewMode === 'REJECTED') {
      return (
        <RejectedPage
          reservation={reservation}
          onReconsider={() => setViewMode('WELCOME')}
        />
      );
    }

    // 5. View Mode: Details Placeholder (Accepted)
    if (viewMode === 'DETAILS_PLACEHOLDER') {
      return (
        <DetailsPlaceholderPage
          reservation={reservation}
          serviceDef={serviceDef}
          onBack={() => setViewMode('WELCOME')}
        />
      );
    }

    // 6. View Mode: Welcome / Accept-Reject Page
    return (
      <WelcomePage
        reservation={reservation}
        serviceDef={serviceDef}
        onAccept={handleAccept}
        onReject={handleReject}
        onExpired={handleExpired}
      />
    );
  };

  return (
    <div className="portal-wrapper">
      <Header />
      {renderContent()}

      {/* Docked Development-Only Preview Controller */}
      <DevStateSwitcher
        currentCategory={catParam}
        currentQNo={qNoParam}
        activePreviewState={activePreviewOverride}
        onSelectPreviewState={handleSelectPreviewState}
        onNavigateDemoUrl={handleNavigateDemoUrl}
        onResetData={handleResetData}
      />
    </div>
  );
};

