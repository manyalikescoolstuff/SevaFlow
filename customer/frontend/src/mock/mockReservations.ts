import { ReservationData } from '../types/reservation';

/**
 * Pre-seeded mock reservations representing tokens proposed by the Raspberry Pi Pico W
 * and acknowledged by the authoritative SevaFlow backend.
 *
 * NOTE: The prompt requires:
 * "Query parameters select a matching mock reservation; they must not create one."
 */

export const INITIAL_MOCK_RESERVATIONS: ReservationData[] = [
  {
    token_id: 'tok-res-001',
    display_number: 'A024',
    service_id: 'svc-aadhaar',
    category: 'aadhar',
    status: 'RESERVED',
    issued_at: new Date(Date.now() - 30000).toISOString(),
    // 5 minutes demo TTL from initial creation
    expires_at: new Date(Date.now() + 270000).toISOString(),
    hardware_reservation_id: 'pico_res_aadhaar_024',
    claim_secret_hash: 'hash_claim_aadhar_024',
    is_registered: false,
  },
  {
    token_id: 'tok-res-002',
    display_number: 'K012',
    service_id: 'svc-aadhaar',
    category: 'kyc',
    status: 'RESERVED',
    issued_at: new Date(Date.now() - 45000).toISOString(),
    expires_at: new Date(Date.now() + 255000).toISOString(),
    hardware_reservation_id: 'pico_res_kyc_012',
    claim_secret_hash: 'hash_claim_kyc_012',
    is_registered: false,
  },
  {
    token_id: 'tok-res-003',
    display_number: 'B024',
    service_id: 'svc-pan',
    category: 'new_account',
    status: 'RESERVED',
    issued_at: new Date(Date.now() - 60000).toISOString(),
    expires_at: new Date(Date.now() + 240000).toISOString(),
    hardware_reservation_id: 'pico_res_new_024',
    claim_secret_hash: 'hash_claim_new_024',
    is_registered: false,
  },
  {
    token_id: 'tok-res-003-b',
    display_number: 'B008',
    service_id: 'svc-pan',
    category: 'new_account',
    status: 'RESERVED',
    issued_at: new Date(Date.now() - 60000).toISOString(),
    expires_at: new Date(Date.now() + 240000).toISOString(),
    hardware_reservation_id: 'pico_res_new_008',
    claim_secret_hash: 'hash_claim_new_008',
    is_registered: false,
  },
  {
    token_id: 'tok-res-004',
    display_number: 'C045',
    service_id: 'svc-income',
    category: 'cash',
    status: 'RESERVED',
    issued_at: new Date(Date.now() - 15000).toISOString(),
    expires_at: new Date(Date.now() + 285000).toISOString(),
    hardware_reservation_id: 'pico_res_cash_045',
    claim_secret_hash: 'hash_claim_cash_045',
    is_registered: false,
  },
  {
    token_id: 'tok-res-005',
    display_number: 'H003',
    service_id: 'svc-land',
    category: 'helpdesk',
    status: 'RESERVED',
    issued_at: new Date(Date.now() - 20000).toISOString(),
    expires_at: new Date(Date.now() + 280000).toISOString(),
    hardware_reservation_id: 'pico_res_help_003',
    claim_secret_hash: 'hash_claim_help_003',
    is_registered: false,
  },
];
