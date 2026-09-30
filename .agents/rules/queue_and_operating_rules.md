# SevaFlow — Queue and Operating Rules

Version 1.0 | Decision snapshot: 28 September 2026, Asia/Kolkata

Based on the project conversation and pasted Antigravity reports. This is a specification, not evidence of tested implementation.

## Authority
This file captures the latest user decisions. The two-recall policy below supersedes every earlier proposal to reinsert a missed token behind two waiting customers. Do not implement old restoration shifts or restoration-time tie-breakers.

## R1. Physical admission and reservations
- One Pico W; each service has its own counter in V1.
- Service selection originates at the device. Exact button count and service-to-button wiring still need matching to available hardware.
- Pico proposes number, reservation ID and URL; backend validates and acknowledges before QR display.
- Reserve is not register. RESERVED and CLAIMED tokens cannot be dispatched.
- Repeated network requests preserve identity and deadline.
- Firmware accepts one continuous touch, requires release and uses the previously agreed five-second cooldown. This prevents accidental repeats, not deliberate repeat issuance by one person.
- Do not hold the device occupied for the whole registration TTL. The exact screen-release/scan acknowledgement protocol needs verification and must not invalidate a customer's still-valid claim.

## R2. Scan order and activation
- The first successful explicit backend claim/scan validation establishes immutable scan order. Camera detection alone is not observable.
- Customer must complete name/phone registration before the reservation deadline.
- Registered waiting customers are dispatched in scan order, subject to due recalls.
- Refreshes and rescans do not change priority.
- If A025 registers while earlier-scanned A024 is still typing, A025 can be called at a free counter. A024 cannot displace it. If both are still waiting when selected, A024 goes first.
- Token number is not people-ahead count. No mandatory preparation checklist.

## R3. Expiry and rejection
Registration-link validity is 3–5 minutes in the original requirement; five minutes is the proposed default, not a separately confirmed final value. Backend sets deadline on first acceptance, with no extension for scans/retries. Check deadline after transaction locks; at or after expiry, reject uncompleted registration.

Expiry does not terminate a registered active token. Reject/release applies to an unclaimed/claim-owned reservation and must not cancel someone else's token. Existing Accept/Reject UI remains until its removal is approved.

## R4. Staff and counters
- Staff operates its assigned counter; Admin monitors.
- Start Service is approved. CALLED and SERVING are distinct.
- Call Next selects an eligible token when the active counter is free.
- Complete & Next completes current service and chooses a due recall or next customer atomically.
- Pause prevents new assignments, without silently completing/cancelling the current customer.
- Staff decides how long to wait for an absent customer. There is no automatic absence timeout.
- A speaker is not required. Recall is a visual/customer-page or integrated notification event, with honest delivery status.

## R5. Two-recall missed-turn rule — approved single-missed-customer sequence
| Step | Counter action | A024 outcome |
|---|---|---|
| Initial call missed | Staff marks missed and calls customer 1 | Pending first recall; same token retained |
| Customer 1 finishes actual service | Recall A024 | Start Service if present |
| First recall absent | Staff marks absent; calls customer 2 | Pending second recall |
| Customer 2 finishes actual service | Recall A024 again | Start Service if present |
| Second recall absent | Staff closes token | Must get a new token and join normally |

The original call is not one of the two recall opportunities. Merely calling, skipping or marking another customer missed does not count as completing service. Ongoing service is never interrupted. A notification retry or repeated HTTP command does not create another opportunity or consume an extra attempt.

After a customer returns at a recall, retain the original token and record the actual service-start event. On final absence, use an explicit closed outcome/reason for recall exhaustion; it is not a completed service and not QR expiry.

## R6. Multiple missed customers — partially decided
FIFO ordering among missed customers is accepted in principle. The detailed scheduler is unresolved. It must explain:
1. Whether all due customers are recalled sequentially after a completion.
2. What happens to remaining due recalls if a recalled customer starts service.
3. How each customer's first/second opportunity is tied to intervening completions.
4. What happens when nobody else is waiting to complete service.
5. End-of-day handling and a paused/closed counter.

Do not label the general recall scheduler finalized until these examples are approved. Do not close tokens merely because no other customer is available.

## R7. Invariants and recovery
- One current assignment per counter; one current counter per token.
- Unregistered, expired, cancelled and recall-exhausted tokens are ineligible.
- Same command retry returns its original result; payload mismatch conflicts.
- A lost initial claim response is recoverable only by the browser with the pre-existing recovery credential, not any holder of the QR.
- Current-token expectation protects against stale Staff actions.
- Backend restart preserves queue and attempts. UI disconnect alone does not mark customers absent.
- Secrets and other customers' personal details never appear in public tracking.

## Decisions still required
Exact TTL; daily versus continuous numbering and reset boundaries; multiple-missed and empty-queue cases; no-show/end-of-day closure; approaching-turn threshold/provider; Accept-screen simplification. Offline admission and shared-phone/token retrieval policies have not been finalized.
