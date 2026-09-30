"""Existing category mapping, exposed explicitly to kiosk clients.

Aadhaar's shared legacy ID is provisional; no hardware button wiring is inferred.
"""
from urllib.parse import urlencode

CATEGORIES = {
    'aadhar': {'service_id': 'svc-aadhaar', 'label': 'Aadhaar Services', 'provisional': True},
    'kyc': {'service_id': 'svc-aadhaar', 'label': 'KYC Verification', 'provisional': False},
    'new_account': {'service_id': 'svc-pan', 'label': 'New Bank Account', 'provisional': False},
    'cash': {'service_id': 'svc-income', 'label': 'Cash Transactions', 'provisional': False},
    'helpdesk': {'service_id': 'svc-land', 'label': 'Help Desk', 'provisional': False},
}

def entry_path(category, service_id, display_number, reservation_id):
    definition = CATEGORIES.get(category)
    if not definition or definition['service_id'] != service_id:
        raise ValueError('Category does not match this service')
    return '/qr?' + urlencode({'cat': category, 'qNo': display_number, 'reservation': reservation_id})
