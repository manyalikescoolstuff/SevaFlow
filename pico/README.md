# Pico W live reservation script

Copy `main.py` to the Pico W using Thonny. Keep your existing `sh1106.py` and
`uQR.py` on the device. This uses the existing FastAPI backend, not a new server.

## Before running

1. Edit `WIFI_SSID`, `WIFI_PASSWORD`, and `HARDWARE_SECRET` in `main.py`.
   The secret must match `HARDWARE_SECRET` on the deployed backend, which may differ
   from a local development `.env`. Do not paste it into chat or a QR code.
2. Check the two configured URLs against your actual deployments:
   - Backend: `https://sevaflow-production.up.railway.app/api/v1`
   - Customer: `https://sevaflow-customer.vercel.app`
   These were taken from the supplied project; their live configuration was not tested.
   Customer and staff API configuration must point to that same backend/database.
3. Save as **Raspberry Pi Pico → main.py**, then run with Thonny's Pico interpreter.
   Use your existing MicroPython firmware supporting `Timer(..., hard=True)`.
4. Additional modules: `requests` (or its `urequests` alias) and `ntptime`.
   If an import is missing, connect the Pico to Wi-Fi from its Thonny shell and
   install through MicroPython's package manager:

   ```python
   import network, time
   wlan = network.WLAN(network.STA_IF)
   wlan.active(True)
   wlan.connect('YOUR_WIFI_NAME', 'YOUR_WIFI_PASSWORD')
   for _ in range(100):
       if wlan.isconnected():
           break
       time.sleep_ms(200)
   # Run these only after wlan.isconnected() returns True:
   import mip
   mip.install('requests')
   mip.install('ntptime')
   ```

The script synchronizes UTC through NTP before issuing/recovering a reservation.
If NTP is blocked, it reports an error instead of showing a potentially expired QR.
Requests must support the `timeout` keyword. See the
[official MicroPython library repository](https://github.com/micropython/micropython-lib)
and [RP2 Wi-Fi documentation](https://docs.micropython.org/en/latest/rp2/quickref.html).

## Preserved wiring

| Component | GPIO / setting |
| --- | --- |
| New account button | GP10, pull-up, active low |
| Cash button | GP11, pull-up, active low |
| Aadhaar / KYC button | GP12, pull-up, active low |
| Help desk button | GP13, pull-up, active low |
| SH1106 OLED | SDA GP16, SCL GP17, address 0x3C, 128×64 |
| Digit selects | GP7, GP6 |
| Seven segments | GP18, GP19, GP20, GP21, GP22, GP26, GP27 |
| Display refresh | Original 500 Hz hard timer |

GP12 retains the original `aadhar` category, which the app maps to `svc-aadhaar`.
If the button specifically means KYC, change just that category to `kyc`.
The unusual service IDs for the other categories match the existing customer app:
new account → `svc-pan`, cash → `svc-income`, help desk → `svc-land`.

## First live check

- Release all buttons, then press one. The OLED connects Wi-Fi, checks the clock,
  and saves a reservation before showing its QR. Thonny should print `BACKEND SAVED`.
- Scan the new QR. It contains reservation credentials and no `preview=1`.
- Accept and complete name, phone, and email registration before the backend deadline.
- Open the live staff page (not `/staff/demo`) for the matching service/counter.
  The token should now be WAITING and available to Call Next.
- A reservation alone is RESERVED and cannot be called. Registration is required.

The QR remains visible for 15 seconds, or less near its deadline. Hiding it does not
cancel the backend reservation. There is no device-side scan acknowledgement.
One press requires a stable release before another press is accepted, with a
five-second cooldown after each network attempt.

The seven-segment serving display still uses your USB commands `SERVE A024`,
`SERVE 34`, and `CLEAR`. Automatic synchronization with staff calls is not included.
Numbers above 99 still display `--`, exactly as in the original script.

## Retry and stored state

`sevaflow-state.json` on the Pico stores counters and an in-flight request before
the first POST. On a timeout, release the buttons and press again to retry the
same reservation. Any button retries that pending request, not a different service.
On reboot, a pending request is recovered the same way. An expired recovered
reservation is cleared without displaying its QR; press again for a new token.

The counter advances when the pending request is saved, so failures can leave gaps.
It starts at 24 only on a fresh installation. For a database already containing
live tokens, choose unused starting numbers before first use. Do not delete the
state file, reformat flash, or clone it to another device to reset numbering.
The current backend does not allocate or enforce globally unique display numbers;
this implementation is for the project's single kiosk. Multiple kiosks or a daily
reset policy would need coordinated backend numbering.

The script uses a temporary file and LittleFS rename to persist state. An invalid
state stops issuance rather than resetting counters. Keep that file when updating
`main.py`. It contains private claim credentials for the pending reservation.

## Errors

| Thonny message | Check |
| --- | --- |
| HTTP 401 | Device secret against deployed backend HARDWARE_SECRET |
| HTTP 404 | Backend URL and seeded service IDs |
| HTTP 422 | Deployed API schema against the local project version |
| HTTP 500 | Backend logs, database connection, and migrations |
| WiFi timeout | Credentials, coverage, and 2.4 GHz network |
| Clock error / timeout before saving | NTP reachability |
| QR exceeds OLED height | Customer domain length / installed uQR variant |
| Missing import | Install the named MicroPython module |

The script intentionally retains uncertain/failed requests; it does not silently
issue a replacement number after an HTTP failure. Fix the reported cause and retry.
HTTP socket timeouts do not necessarily bound DNS lookup time in MicroPython.

## Verification and limits

Desktop tests in `verification/host_checks.py` passed for all four service mappings,
QR credential hashes, persistence across simulated reboot, identical retry payloads,
expired acknowledgements, failed/mismatched responses, and disk-write failure.
Syntax was checked with CPython. Hardware and HTTP in these tests are simulated.

Using [upstream uQR](https://github.com/JASchilz/uQR), the configured URLs produce
57×57 matrices including the quiet zone, rendered at one pixel per module. The
script also checks the actual installed library's output before reserving a token.
Physical phone scanning, GPIO timing under TLS load, device memory, firmware
compatibility, and live deployment behavior have not been tested on your Pico.
The upstream library in `verification/uQR_reference.py` is for desktop checks;
you do not need to copy that verification folder to the Pico.

The standard MicroPython requests library uses its own TLS defaults; this script
does not add CA certificate provisioning or certificate validation. Treat it as
an integration build, not a completed production security configuration.
