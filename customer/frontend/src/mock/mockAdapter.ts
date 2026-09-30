import { 
  ClaimValidationResult, 
  MockPreviewState, 
  ReservationData 
} from '../types/reservation';
import { INITIAL_MOCK_RESERVATIONS } from './mockReservations';
import { getServiceDefinition } from '../config/services';

const STORAGE_KEY_RESERVATIONS = 'sevaflow_mock_reservations';
const STORAGE_KEY_SESSION = 'sevaflow_browser_session_id';
const STORAGE_KEY_PREVIEW_STATE = 'sevaflow_dev_preview_state';

// Generate or retrieve persistent browser session ID
export function getOrCreateBrowserSessionId(): string {
  let sessionId = localStorage.getItem(STORAGE_KEY_SESSION);
  if (!sessionId) {
    sessionId = 'session_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
    localStorage.setItem(STORAGE_KEY_SESSION, sessionId);
  }
  return sessionId;
}

// Retrieve or initialize reservations from localStorage
export function getStoredReservations(): ReservationData[] {
  const raw = localStorage.getItem(STORAGE_KEY_RESERVATIONS);
  if (!raw) {
    localStorage.setItem(STORAGE_KEY_RESERVATIONS, JSON.stringify(INITIAL_MOCK_RESERVATIONS));
    return INITIAL_MOCK_RESERVATIONS;
  }
  try {
    const parsed: ReservationData[] = JSON.parse(raw);
    const missing = INITIAL_MOCK_RESERVATIONS.filter(
      init => !parsed.some(p => p.token_id === init.token_id || p.display_number.toUpperCase() === init.display_number.toUpperCase())
    );
    if (missing.length > 0) {
      const merged = [...parsed, ...missing];
      localStorage.setItem(STORAGE_KEY_RESERVATIONS, JSON.stringify(merged));
      return merged;
    }
    return parsed;
  } catch {
    localStorage.setItem(STORAGE_KEY_RESERVATIONS, JSON.stringify(INITIAL_MOCK_RESERVATIONS));
    return INITIAL_MOCK_RESERVATIONS;
  }
}

export function saveReservations(reservations: ReservationData[]): void {
  localStorage.setItem(STORAGE_KEY_RESERVATIONS, JSON.stringify(reservations));
}

// Dev preview state override
export function getDevPreviewState(): MockPreviewState | null {
  return localStorage.getItem(STORAGE_KEY_PREVIEW_STATE) as MockPreviewState | null;
}

export function setDevPreviewState(state: MockPreviewState | null): void {
  if (state) {
    localStorage.setItem(STORAGE_KEY_PREVIEW_STATE, state);
  } else {
    localStorage.removeItem(STORAGE_KEY_PREVIEW_STATE);
  }
}

// Reset everything to defaults
export function resetMockData(): void {
  localStorage.removeItem(STORAGE_KEY_PREVIEW_STATE);
  // Re-seed with fresh 5-minute countdowns from current moment
  const fresh = INITIAL_MOCK_RESERVATIONS.map((r, idx) => ({
    ...r,
    status: 'RESERVED' as const,
    is_registered: false,
    browser_owner_id: undefined,
    claim_session_id: undefined,
    issued_at: new Date(Date.now() - (idx * 15000)).toISOString(),
    expires_at: new Date(Date.now() + 300000 - (idx * 15000)).toISOString(),
  }));
  saveReservations(fresh);
}

/**
 * Validates the QR query parameters against authoritative mock reservations.
 * Enforces all invariant rules:
 * - Query parameters select a matching reservation; they must NOT create one.
 * - Missing parameters, unsupported categories, and unknown/mismatched tokens return clear errors.
 * - Enforces fixed deadline expiry.
 */
export async function validateClaimRequest(
  cat: string | null,
  qNo: string | null,
  previewOverride?: MockPreviewState | null
): Promise<ClaimValidationResult> {
  // Simulate network latency (250ms)
  await new Promise(resolve => setTimeout(resolve, 250));

  const activeOverride = previewOverride !== undefined ? previewOverride : getDevPreviewState();

  // 1. Connection error simulation
  if (activeOverride === 'connection_error') {
    return {
      success: false,
      errorCode: 'NETWORK_ERROR',
      errorMessage: 'Could not connect to SevaFlow queue service. Please check your network connection.',
    };
  }

  // 2. Validate parameter presence
  if (!cat || !qNo) {
    return {
      success: false,
      errorCode: 'MISSING_PARAMS',
      errorMessage: 'Missing QR code parameters. Please scan an authentic token QR code from the SevaFlow kiosk.',
    };
  }

  // 3. Validate service category support
  const serviceDef = getServiceDefinition(cat);
  if (!serviceDef) {
    return {
      success: false,
      errorCode: 'UNSUPPORTED_CATEGORY',
      errorMessage: `Service category "${cat}" is not recognized or supported by this service center.`,
    };
  }

  // 4. Force invalid/mismatched simulation
  if (activeOverride === 'invalid_mismatched') {
    return {
      success: false,
      errorCode: 'MISMATCHED_RESERVATION',
      errorMessage: `No active reservation found for token "${qNo}" under "${serviceDef.label}". Please check your token slip.`,
    };
  }

  // 5. Look up matching reservation (must match both category and qNo)
  const reservations = getStoredReservations();
  const currentSessionId = getOrCreateBrowserSessionId();

  const normalizedQNo = qNo.trim().toUpperCase();
  const reservation = reservations.find(r => 
    r.category === serviceDef.key && 
    r.display_number.toUpperCase() === normalizedQNo
  );

  if (!reservation) {
    return {
      success: false,
      errorCode: 'MISMATCHED_RESERVATION',
      errorMessage: `No active reservation found matching token "${qNo}" for service "${serviceDef.label}".`,
    };
  }

  // 6. Handle Dev preview state overrides on this reservation
  if (activeOverride === 'expired') {
    return {
      success: false,
      errorCode: 'EXPIRED',
      errorMessage: 'This token registration window has expired. Please touch the kiosk to request a new token.',
      reservation: {
        ...reservation,
        status: 'EXPIRED',
        expires_at: new Date(Date.now() - 60000).toISOString(),
      },
    };
  }

  if (activeOverride === 'claimed_other') {
    return {
      success: false,
      errorCode: 'CLAIMED_BY_ANOTHER',
      errorMessage: 'This token reservation is already claimed by another browser session. To recover, use the original scanning device.',
      reservation: {
        ...reservation,
        status: 'CLAIMED',
        browser_owner_id: 'other_browser_session_9988',
      },
    };
  }

  if (activeOverride === 'already_registered') {
    return {
      success: false,
      errorCode: 'ALREADY_REGISTERED',
      errorMessage: 'This token has already completed registration and is currently active in the queue.',
      reservation: {
        ...reservation,
        status: 'WAITING',
        is_registered: true,
        scan_sequence: 14,
        queue_position: 3,
      },
    };
  }

  if (activeOverride === 'rejected') {
    return {
      success: false,
      errorCode: 'REJECTED_SESSION',
      errorMessage: 'This token was previously declined by the user.',
      reservation: {
        ...reservation,
        status: 'REJECTED',
      },
    };
  }

  // 7. Check natural expiry from fixed expires_at timestamp
  const now = new Date().getTime();
  const expiryTime = new Date(reservation.expires_at).getTime();
  if (now >= expiryTime) {
    return {
      success: false,
      errorCode: 'EXPIRED',
      errorMessage: 'Registration deadline expired. Please request a new token at the kiosk.',
      reservation,
    };
  }

  // 8. Check if already registered
  if (reservation.is_registered || reservation.status === 'WAITING') {
    return {
      success: false,
      errorCode: 'ALREADY_REGISTERED',
      reservation,
    };
  }

  // 9. Check if claimed by another browser
  if (reservation.browser_owner_id && reservation.browser_owner_id !== currentSessionId) {
    return {
      success: false,
      errorCode: 'CLAIMED_BY_ANOTHER',
      errorMessage: 'This reservation is already claimed on another device.',
      reservation,
    };
  }

  // 10. Check if rejected
  if (reservation.status === 'REJECTED') {
    return {
      success: false,
      errorCode: 'REJECTED_SESSION',
      errorMessage: 'You have rejected this reservation.',
      reservation,
    };
  }

  // Valid reservation ready for Welcome/Accept-Reject review
  return {
    success: true,
    reservation,
  };
}

/**
 * Mock Accept Action:
 * Claims the token session without activating the token or completing full registration.
 */
export function mockAcceptReservation(tokenId: string): ReservationData | null {
  const reservations = getStoredReservations();
  const currentSessionId = getOrCreateBrowserSessionId();

  const index = reservations.findIndex(r => r.token_id === tokenId);
  if (index === -1) return null;

  reservations[index] = {
    ...reservations[index],
    status: 'CLAIMED',
    browser_owner_id: currentSessionId,
    claim_session_id: 'claim_' + Math.random().toString(36).substring(2, 9),
  };

  saveReservations(reservations);
  return reservations[index];
}

/**
 * Mock Reject Action:
 * Marks the token as REJECTED in the mock session.
 */
export function mockRejectReservation(tokenId: string): ReservationData | null {
  const reservations = getStoredReservations();
  const currentSessionId = getOrCreateBrowserSessionId();

  const index = reservations.findIndex(r => r.token_id === tokenId);
  if (index === -1) return null;

  reservations[index] = {
    ...reservations[index],
    status: 'REJECTED',
    browser_owner_id: currentSessionId,
  };

  saveReservations(reservations);
  return reservations[index];
}
