import { ServiceCategoryKey, ServiceDefinition } from '../types/reservation';

/**
 * Single source of truth for SevaFlow service categories, UI labels,
 * backend service ID mappings, and informational document checklists.
 *
 * NOTE ON AUTHORITY & PRESERVATION:
 * - 'aadhar' is explicitly preserved as a distinct service category per specification.
 * - 'aadhar' is NOT silently equated with KYC.
 * - Official hardware button services: KYC, New Bank Account, Cash Transactions, and Help Desk.
 * - Where hardware mappings are provisional/demo, they are clearly marked.
 */

export const SERVICE_REGISTRY: Record<ServiceCategoryKey, ServiceDefinition> = {
  aadhar: {
    key: 'aadhar',
    label: 'Aadhaar Services',
    backendServiceId: 'svc-aadhaar',
    buttonLabel: 'Aadhaar Services',
    isProvisional: true,
    provisionalNote: 'Dedicated Aadhaar Desk — Hardware dispenser demo mapping (Preserved distinct from KYC).',
    description: 'Biometric update, address correction, and demographic changes for Unique Identification.',
    documentsChecklist: [
      'Original Proof of Identity (Voter ID, Passport, PAN Card, Driving Licence)',
      'Proof of Address (Utility Bill < 3 months, Bank Passbook, Ration Card)',
      'Active Mobile Phone registered with Aadhaar (for receiving verification OTP)',
      'Original supporting document for demographic correction (Birth Certificate, Marriage Certificate)',
    ],
  },

  kyc: {
    key: 'kyc',
    label: 'KYC Verification',
    backendServiceId: 'svc-aadhaar',
    buttonLabel: 'KYC (Button 1)',
    isProvisional: false,
    description: 'Citizen Re-KYC, customer verification, and biometric identification verification.',
    documentsChecklist: [
      'Original Aadhaar Card & PAN Card',
      'Recent passport-size colour photograph',
      'Existing Account Passbook or Certificate copy',
    ],
  },

  new_account: {
    key: 'new_account',
    label: 'New Bank Account',
    backendServiceId: 'svc-pan',
    buttonLabel: 'New Bank Account (Button 2)',
    isProvisional: false,
    description: 'Savings, current account opening, and citizen onboarding.',
    documentsChecklist: [
      'Valid Government Photo ID (Aadhaar, Voter ID, PAN Card)',
      'Two recent passport-size colour photographs',
      'Initial deposit cash or draft',
      'Proof of permanent and communication address',
    ],
  },

  cash: {
    key: 'cash',
    label: 'Cash Transactions',
    backendServiceId: 'svc-income',
    buttonLabel: 'Cash Transactions (Button 3)',
    isProvisional: false,
    description: 'Cash deposits, withdrawals, and fee disbursement counters.',
    documentsChecklist: [
      'Account Passbook / Registered Citizen Card',
      'Cash Denomination Slip (PAN Card mandatory if depositing > ₹50,000)',
      'Valid Government ID for cash withdrawals',
    ],
  },

  helpdesk: {
    key: 'helpdesk',
    label: 'Help Desk',
    backendServiceId: 'svc-land',
    buttonLabel: 'Help Desk (Button 4)',
    isProvisional: false,
    description: 'Citizen enquiry, form assistance, and queue direction.',
    documentsChecklist: [
      'Previous token slip or application acknowledgement (if available)',
      'Description of query or government department referral document',
    ],
  },
};

/**
 * Helper to retrieve service definition by category key.
 * Returns null if the category is unsupported.
 */
export function getServiceDefinition(cat: string | null | undefined): ServiceDefinition | null {
  if (!cat) return null;
  const normalized = cat.trim().toLowerCase();
  
  // Support aliases while preserving strict keys
  if (normalized === 'aadhar' || normalized === 'aadhaar') {
    return SERVICE_REGISTRY.aadhar;
  }
  if (normalized === 'kyc') {
    return SERVICE_REGISTRY.kyc;
  }
  if (normalized === 'new_account' || normalized === 'account' || normalized === 'bank' || normalized === 'pan') {
    return SERVICE_REGISTRY.new_account;
  }
  if (normalized === 'cash' || normalized === 'income') {
    return SERVICE_REGISTRY.cash;
  }
  if (normalized === 'helpdesk' || normalized === 'help' || normalized === 'land') {
    return SERVICE_REGISTRY.helpdesk;
  }

  return null;
}
