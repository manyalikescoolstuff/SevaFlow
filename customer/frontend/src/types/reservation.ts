/**
 * Data contracts and state types for SevaFlow Customer Reservation & Claim lifecycle.
 */

export type ServiceCategoryKey = 'aadhar' | 'kyc' | 'new_account' | 'cash' | 'helpdesk';

export type ReservationStatus = 
  | 'RESERVED'
  | 'CLAIMED'
  | 'WAITING'
  | 'REJECTED'
  | 'EXPIRED';

export type MockPreviewState = 
  | 'loading'
  | 'valid'
  | 'expired'
  | 'invalid_mismatched'
  | 'rejected'
  | 'claimed_other'
  | 'already_registered'
  | 'connection_error';

export interface ServiceDefinition {
  key: ServiceCategoryKey;
  label: string;
  backendServiceId: string;
  buttonLabel: string;
  isProvisional: boolean;
  provisionalNote?: string;
  description: string;
  documentsChecklist: string[];
}

export interface ReservationData {
  token_id: string;
  display_number: string;
  service_id: string;
  category: ServiceCategoryKey;
  status: ReservationStatus;
  issued_at: string;
  expires_at: string;
  hardware_reservation_id: string;
  claim_secret_hash: string;
  claim_session_id?: string;
  browser_owner_id?: string;
  is_registered: boolean;
  scan_sequence?: number;
  queue_position?: number;
}

export interface ClaimValidationResult {
  success: boolean;
  reservation?: ReservationData;
  errorCode?: 
    | 'MISSING_PARAMS'
    | 'UNSUPPORTED_CATEGORY'
    | 'MISMATCHED_RESERVATION'
    | 'EXPIRED'
    | 'CLAIMED_BY_ANOTHER'
    | 'ALREADY_REGISTERED'
    | 'REJECTED_SESSION'
    | 'NETWORK_ERROR';
  errorMessage?: string;
}
