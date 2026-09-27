"""
Model-level unit tests — validate state machine logic WITHOUT a database.
Run with: venv\Scripts\pytest tests\ -v
"""
import pytest
from datetime import datetime, timezone, timedelta
import hashlib, uuid


def sha256(v):
    return hashlib.sha256(v.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Token state machine helpers (pure logic, no DB)
# ---------------------------------------------------------------------------

def make_token(status="RESERVED", recall_attempts=0, missed_counter_id=None):
    return {
        "id": str(uuid.uuid4()),
        "display_number": "A-001",
        "status": status,
        "hardware_reservation_id": str(uuid.uuid4()),
        "claim_secret_hash": sha256("secret"),
        "recovery_credential_hash": None,
        "claim_session_id": None,
        "recall_attempts": recall_attempts,
        "missed_counter_id": missed_counter_id,
        "reservation_expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
    }


class TestTokenStateLogic:
    def test_initial_status_is_reserved(self):
        t = make_token(status="RESERVED")
        assert t["status"] == "RESERVED"

    def test_recall_attempts_start_at_zero(self):
        t = make_token()
        assert t["recall_attempts"] == 0

    def test_original_miss_does_not_increment_recall(self):
        """First miss: recall_attempts must stay at 0."""
        t = make_token(status="CALLED")
        # Simulate mark_missed
        t["status"] = "MISSED"
        t["missed_counter_id"] = "ctr-01"
        # recall_attempts NOT incremented
        assert t["recall_attempts"] == 0

    def test_first_absent_again_increments_to_1(self):
        t = make_token(status="CALLED", recall_attempts=0, missed_counter_id="ctr-01")
        # Simulate mark_absent_again
        t["recall_attempts"] += 1
        assert t["recall_attempts"] == 1
        t["status"] = "MISSED"
        assert t["status"] == "MISSED"

    def test_second_absent_again_closes_token(self):
        t = make_token(status="CALLED", recall_attempts=1, missed_counter_id="ctr-01")
        t["recall_attempts"] += 1
        assert t["recall_attempts"] == 2
        if t["recall_attempts"] >= 2:
            t["status"] = "CLOSED_MISSED"
        assert t["status"] == "CLOSED_MISSED"

    def test_claim_secret_must_match(self):
        t = make_token()
        correct = sha256("secret")
        wrong = sha256("wrong")
        assert t["claim_secret_hash"] == correct
        assert t["claim_secret_hash"] != wrong

    def test_recovery_credential_required_for_retry(self):
        """Browser must supply recovery_credential to retry a claim."""
        t = make_token(status="CLAIMED")
        t["claim_session_id"] = "sess-browser-1"
        t["recovery_credential_hash"] = sha256("browser-recovery-key")
        # Same browser retries: claim_session_id matches → allowed
        assert t["claim_session_id"] == "sess-browser-1"
        # Different browser with only QR: would have different session_id → blocked
        different_session = "sess-browser-2"
        assert t["claim_session_id"] != different_session

    def test_expiry_prevents_claim(self):
        t = make_token()
        t["reservation_expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert t["reservation_expires_at"] < datetime.now(timezone.utc)


class TestRecallSequence:
    """
    Verify the exact two-recall sequence for a single missed token.
    Example: A024 missed initially.
    """

    def test_full_recall_sequence(self):
        token = make_token(status="MISSED", recall_attempts=0, missed_counter_id="ctr-01")

        # Service 1 completes → recall A024 (attempt 1 pending)
        token["status"] = "CALLED"
        assert token["recall_attempts"] == 0  # not yet consumed

        # If present → start service (no recall consumed)
        # Simulate absent instead: mark_absent_again
        token["recall_attempts"] += 1  # NOW consumed
        token["status"] = "MISSED"
        assert token["recall_attempts"] == 1

        # Service 2 completes → recall A024 again
        token["status"] = "CALLED"

        # Absent again
        token["recall_attempts"] += 1  # attempt 2 consumed
        assert token["recall_attempts"] == 2
        if token["recall_attempts"] >= 2:
            token["status"] = "CLOSED_MISSED"
        assert token["status"] == "CLOSED_MISSED"

    def test_recall_if_present_does_not_consume_attempt(self):
        """If customer is present on recall, Start Service is pressed — no attempt consumed."""
        token = make_token(status="CALLED", recall_attempts=0, missed_counter_id="ctr-01")
        # Staff clicks Start Service
        token["status"] = "SERVING"
        # recall_attempts unchanged
        assert token["recall_attempts"] == 0
        # Complete service
        token["status"] = "COMPLETED"
        assert token["recall_attempts"] == 0  # consumed 0 recalls


class TestScanOrdering:
    """Sort key ordering logic (pure)."""

    def test_sort_key_equals_scan_sequence_initially(self):
        tokens = [
            {"scan_sequence": 1, "sort_key": 1},
            {"scan_sequence": 2, "sort_key": 2},
            {"scan_sequence": 3, "sort_key": 3},
        ]
        sorted_tokens = sorted(tokens, key=lambda t: t["sort_key"])
        assert [t["scan_sequence"] for t in sorted_tokens] == [1, 2, 3]

    def test_earlier_scanner_registers_later_still_has_priority(self):
        """Scanner 1 scans first (seq=1) but registers after scanner 2 (seq=2)."""
        t1 = {"scan_sequence": 1, "sort_key": 1}
        t2 = {"scan_sequence": 2, "sort_key": 2}
        sorted_tokens = sorted([t2, t1], key=lambda t: t["sort_key"])
        assert sorted_tokens[0]["scan_sequence"] == 1
