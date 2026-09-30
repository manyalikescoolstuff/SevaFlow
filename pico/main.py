"""SevaFlow Pico W: real reservations against the existing FastAPI backend.

Copy to Pico as main.py alongside sh1106.py and uQR.py.
Requires MicroPython requests, ntptime, and Timer(hard=True).
Edit configuration below. Never delete sevaflow-state.json to reset numbering.
USB: SERVE A024, SERVE 34, CLEAR. Staff display sync is still manual.
"""
from machine import Pin, SoftI2C, Timer, unique_id
from time import sleep_ms, sleep_us, ticks_ms, ticks_diff
from sh1106 import SH1106_I2C
from uQR import QRCode
import micropython
import network
import ntptime
import time
import os
import json
import hashlib
import binascii
import select
import sys
import gc
try:
    import requests
except ImportError:
    import urequests as requests

# EDIT THESE THREE VALUES. Use the HARDWARE_SECRET of the SAME deployed backend.
WIFI_SSID = 'YOUR_WIFI_NAME'
WIFI_PASSWORD = 'YOUR_WIFI_PASSWORD'
HARDWARE_SECRET = 'YOUR_BACKEND_HARDWARE_SECRET'

# Defaults taken from this project's deployment configuration; verify your deployment.
API_BASE_URL = 'https://sevaflow-production.up.railway.app/api/v1'
CUSTOMER_BASE_URL = 'https://sevaflow-customer.vercel.app'
DEVICE_ID = 'pico-' + binascii.hexlify(unique_id()).decode()
QR_VISIBLE_MS = 15000
COOLDOWN_MS = 5000
WIFI_TIMEOUT_MS = 20000
HTTP_TIMEOUT_SECONDS = 15
START_NUMBER = 24  # First installation only; existing saved counters take precedence.
INITIAL_SERVING_TOKEN = None
STATE_FILE = 'sevaflow-state.json'

# Preserve YOUR physical button order and pins, using existing frontend service IDs.
# GPIO, menu label, URL category, token prefix, backend service ID
SERVICES = (
    (10, '1 New account', 'new_account', 'B', 'svc-pan'),
    (11, '2 Cash', 'cash', 'C', 'svc-income'),
    (12, '3 Aadhaar / KYC', 'aadhar', 'A', 'svc-aadhaar'),
    (13, '4 Help desk', 'helpdesk', 'H', 'svc-land'),
)
# GP12 retains your original Aadhaar category. Use 'kyc' if this button is KYC only.
PATTERNS = (
    (0,0,0,0,0,0,1), (1,0,0,1,1,1,1),
    (0,0,1,0,0,1,0), (0,0,0,0,1,1,0),
    (1,0,0,1,1,0,0), (0,1,0,0,1,0,0),
    (0,1,0,0,0,0,0), (0,0,0,1,1,1,1),
    (0,0,0,0,0,0,0), (0,0,0,0,1,0,0),
)
BLANK = (1,1,1,1,1,1,1)
DASH = (1,1,1,1,1,1,0)
digits = (Pin(7, Pin.OUT, value=1), Pin(6, Pin.OUT, value=1))
segments = tuple(Pin(gp, Pin.OUT, value=1) for gp in (18,19,20,21,22,26,27))
display_frame = (BLANK, BLANK)
phase = 0
micropython.alloc_emergency_exception_buf(100)


def refresh_display(timer):
    # Original hard IRQ: no network, printing, QR generation or allocation.
    global phase
    digits[0].value(1)
    digits[1].value(1)
    sleep_us(10)
    levels = display_frame[phase]
    i = 0
    while i < 7:
        segments[i].value(levels[i])
        i += 1
    digits[phase].value(0)
    phase = 1 - phase


def set_serving(token):
    global display_frame
    if token is None:
        display_frame = (BLANK, BLANK)
        print('SERVING: none')
        return
    text = str(token).strip().upper()
    numeric = text[1:] if text and 'A' <= text[0] <= 'Z' else text
    if not numeric or not numeric.isdigit():
        raise ValueError('Use SERVE A024 or SERVE 24')
    number = int(numeric)
    if number > 99:
        display_frame = (DASH, DASH)
        print('SERVING:', text, '- exceeds two digits; showing --')
    else:
        display_frame = (PATTERNS[number // 10], PATTERNS[number % 10])
        print('SERVING:', text)


def show_message(oled, *lines):
    oled.fill(0)
    for i, line in enumerate(lines[:5]):
        oled.text(str(line)[:16], 0, i * 12, 1)
    oled.show()


def show_menu(oled):
    oled.fill(0)
    oled.text('SevaFlow LIVE', 0, 0, 1)
    for i, service in enumerate(SERVICES):
        oled.text(service[1], 0, 16 + i * 12, 1)
    oled.show()


def qr_matrix(url):
    gc.collect()
    # uQR default error correction and four-module quiet zone are preserved.
    qr = QRCode()
    qr.add_data(url)
    matrix = qr.get_matrix()
    if len(matrix) > 64:
        raise ValueError('QR exceeds OLED height; use a shorter customer domain')
    return matrix


def show_qr(oled, matrix):
    size = len(matrix)
    scale = min(128 // size, 64 // size)
    x0, y0 = (128 - size * scale) // 2, (64 - size * scale) // 2
    oled.fill(1)
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if dark:
                oled.fill_rect(x0+x*scale, y0+y*scale, scale, scale, 0)
    oled.show()
    print('QR matrix:', size, 'scale:', scale)


def digest(text):
    return binascii.hexlify(hashlib.sha256(text.encode()).digest()).decode()


def save_state(state):
    # Pico MicroPython LittleFS rename replaces the file atomically. Commit disk
    # state BEFORE sending a request; never remove the old file before rename.
    payload = json.dumps(state)
    with open(STATE_FILE + '.tmp', 'w') as handle:
        json.dump({'payload': payload, 'sha256': digest(payload)}, handle)
        handle.flush()
    os.sync()
    os.rename(STATE_FILE + '.tmp', STATE_FILE)
    os.sync()


def load_state():
    if STATE_FILE not in os.listdir():
        # No reservation can have been sent before the first successful save.
        if STATE_FILE + '.tmp' in os.listdir():
            raise RuntimeError('Incomplete state file: inspect in Thonny before proceeding')
        state = {'version': 1, 'device_id': DEVICE_ID,
                 'next_numbers': [START_NUMBER] * len(SERVICES), 'pending': None}
        save_state(state)
        return state
    try:
        with open(STATE_FILE) as handle:
            envelope = json.load(handle)
        if digest(envelope['payload']) != envelope['sha256']:
            raise ValueError('checksum')
        state = json.loads(envelope['payload'])
        if state['version'] != 1 or state['device_id'] != DEVICE_ID:
            raise ValueError('device/version')
        numbers = state['next_numbers']
        if len(numbers) != len(SERVICES) or any(not isinstance(n, int) or n < 1 for n in numbers):
            raise ValueError('counters')
        state['pending']
        return state
    except Exception:
        raise RuntimeError('Saved state is invalid; do not reset counters or issue tokens')


def random_hex():
    # 128-bit random credentials; compact enough for the small OLED QR.
    return binascii.hexlify(os.urandom(16)).decode()


def build_pending(state, index):
    service = SERVICES[index]
    secret = random_hex()
    reservation = random_hex()
    number = '{}{:03d}'.format(service[3], state['next_numbers'][index])
    # All variable URL fields below are controlled ASCII identifiers or hex.
    url = '{}/qr?cat={}&qNo={}&reservation={}#claim={}'.format(
        CUSTOMER_BASE_URL.rstrip('/'), service[2], number, reservation, secret)
    return {'index': index, 'url': url, 'api_base': API_BASE_URL.rstrip('/'),
            'payload': {'device_id': DEVICE_ID, 'hardware_request_id': random_hex(),
                        'hardware_reservation_id': reservation, 'service_id': service[4],
                        'display_number': number, 'claim_secret_hash': digest(secret),
                        'category': service[2]}}


def connect_wifi(oled):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        show_message(oled, 'Connecting WiFi', 'Please wait...')
        wlan.disconnect()
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        started = ticks_ms()
        while not wlan.isconnected():
            if ticks_diff(ticks_ms(), started) >= WIFI_TIMEOUT_MS:
                wlan.disconnect()
                raise OSError('WiFi timeout; check SSID/password and 2.4 GHz WiFi')
            sleep_ms(100)
    return wlan


def sync_clock():
    # Required for checking old idempotent replies after restart. Do not display
    # an already-expired reservation merely because its original reply was 201.
    ntptime.timeout = 5
    ntptime.settime()
    if time.gmtime()[0] < 2026:
        raise OSError('Clock synchronization failed')


def expiry_epoch(value):
    # FastAPI returns ISO UTC with +00:00 (or Z). Avoid a local timezone assumption.
    if not isinstance(value, str) or not (value.endswith('+00:00') or value.endswith('Z')):
        raise ValueError('Backend expiry is not UTC')
    return time.mktime((int(value[0:4]), int(value[5:7]), int(value[8:10]),
                        int(value[11:13]), int(value[14:16]), int(value[17:19]), 0, 0))


def reserve(pending):
    if pending['api_base'] != API_BASE_URL.rstrip('/'):
        raise ValueError('Pending reservation belongs to a different backend')
    response = None
    try:
        gc.collect()
        response = requests.post(pending['api_base'] + '/hardware/tokens',
            headers={'Content-Type': 'application/json', 'X-Hardware-Secret': HARDWARE_SECRET},
            data=json.dumps(pending['payload']), timeout=HTTP_TIMEOUT_SECONDS)
        if response.status_code not in (200, 201):
            # Do not print response bodies: proxies may echo credentials.
            raise OSError('Reservation HTTP {}; pending request retained'.format(response.status_code))
        data = response.json()
        if (data.get('acknowledged') is not True or not data.get('token_id') or
                data.get('display_number') != pending['payload']['display_number']):
            raise ValueError('Invalid acknowledgement; pending request retained')
        deadline = expiry_epoch(data.get('reservation_expires_at'))
        return data, deadline
    finally:
        if response is not None:
            response.close()


def clear_pending(state):
    state['pending'] = None
    save_state(state)


def issue_or_recover(oled, state, index):
    connect_wifi(oled)
    show_message(oled, 'Checking clock', 'Please wait...')
    sync_clock()
    if state['pending'] is None:
        pending = build_pending(state, index)
        # Check QR size BEFORE reserving or consuming a number; release matrix
        # before TLS to reduce Pico heap pressure.
        matrix = qr_matrix(pending['url'])
        del matrix
        state['pending'] = pending
        state['next_numbers'][index] += 1
        save_state(state)
    pending = state['pending']
    show_message(oled, 'Saving token', pending['payload']['display_number'], 'Please wait...')
    data, deadline = reserve(pending)
    if deadline - time.time() < 5:
        clear_pending(state)
        show_message(oled, 'Old QR expired', 'Press for new', 'token')
        print('Old reservation expired; no QR displayed. Press again for a new token.')
        return None
    matrix = qr_matrix(pending['url'])
    # QR generation itself can take time. Check again immediately before display.
    remaining_ms = int((deadline - time.time()) * 1000)
    if remaining_ms < 5000:
        clear_pending(state)
        show_message(oled, 'Old QR expired', 'Press for new', 'token')
        return None
    show_qr(oled, matrix)
    print('BACKEND SAVED:', data['display_number'], 'token_id:', data['token_id'])
    print('Complete customer registration to enter the staff waiting queue.')
    # Keep pending on disk while QR is visible. A restart replays the SAME request.
    # Do not print the private QR claim credential in console logs.
    return min(QR_VISIBLE_MS, remaining_ms)


def handle_command(line):
    line = line.strip()
    if line.upper() == 'CLEAR':
        set_serving(None)
    elif line.upper().startswith('SERVE '):
        try:
            set_serving(line[6:])
        except ValueError as exc:
            print('Command error:', exc)
    elif line:
        print('Commands: SERVE A024, SERVE 34, CLEAR')


def main():
    timer = Timer(-1)
    oled = None
    try:
        try:
            timer.init(freq=500, mode=Timer.PERIODIC, callback=refresh_display, hard=True)
        except TypeError:
            raise RuntimeError('This firmware needs MicroPython with hard=True timers')
        set_serving(INITIAL_SERVING_TOKEN)
        i2c = SoftI2C(sda=Pin(16), scl=Pin(17), freq=100000)
        if 0x3C not in i2c.scan():
            raise RuntimeError('OLED 0x3C not detected; check wiring')
        oled = SH1106_I2C(128, 64, i2c, None, 0x3C)
        oled.sleep(False)
        if WIFI_SSID == 'YOUR_WIFI_NAME' or HARDWARE_SECRET == 'YOUR_BACKEND_HARDWARE_SECRET':
            raise RuntimeError('Edit WIFI_SSID, WIFI_PASSWORD and HARDWARE_SECRET first')
        state = load_state()
        buttons = [Pin(s[0], Pin.IN, Pin.PULL_UP) for s in SERVICES]
        raw = [b.value() for b in buttons]
        stable = raw[:]
        changed = [ticks_ms()] * len(buttons)
        armed = False  # Must observe all buttons released, including after blocking I/O.
        last_attempt = None
        qr_started = None
        qr_duration = QR_VISIBLE_MS
        poller = select.poll()
        poller.register(sys.stdin, select.POLLIN)
        command = ''
        if state['pending']:
            show_message(oled, 'Pending token', 'Press any key', 'to retry same QR')
            print('Saved pending token: next button retries that same reservation.')
        else:
            show_menu(oled)
        print('LIVE backend reservations. USB: SERVE A024, SERVE 34, CLEAR')
        while True:
            now = ticks_ms()
            if poller.poll(0):
                char = sys.stdin.read(1)
                if char in ('\n', '\r'):
                    handle_command(command)
                    command = ''
                elif char:
                    command += char
                    if len(command) > 80:
                        command = ''
            if qr_started is not None and ticks_diff(now, qr_started) >= qr_duration:
                # Hiding the OLED never cancels the customer's backend reservation.
                clear_pending(state)
                show_menu(oled)
                qr_started = None
            cooldown_done = last_attempt is None or ticks_diff(now, last_attempt) >= COOLDOWN_MS
            if (qr_started is None and cooldown_done and
                    all(b.value() == 1 for b in buttons) and all(v == 1 for v in stable) and
                    all(ticks_diff(now, t) >= 50 for t in changed)):
                armed = True
            for i, button in enumerate(buttons):
                value = button.value()
                if value != raw[i]:
                    raw[i] = value
                    changed[i] = now
                elif value != stable[i] and ticks_diff(now, changed[i]) >= 50:
                    stable[i] = value
                    if value == 0 and armed and qr_started is None and cooldown_done:
                        armed = False
                        try:
                            duration = issue_or_recover(oled, state, i)
                            if duration is not None:
                                qr_duration = duration
                                qr_started = ticks_ms()
                        except Exception as exc:
                            # Reload committed state: a failed disk write must never
                            # allow sending an unsaved identity on the next attempt.
                            state = load_state()
                            print('Reservation failed:', type(exc).__name__, str(exc))
                            show_message(oled, 'Not ready', 'See Thonny error', 'Release buttons', 'then press retry')
                        last_attempt = ticks_ms()
                        # Discard button transitions that occurred during network work.
                        raw = [b.value() for b in buttons]
                        stable = raw[:]
                        changed = [last_attempt] * len(buttons)
                        break
            sleep_ms(5)
    except Exception:
        if oled is not None:
            show_message(oled, 'Setup / state', 'error', 'See Thonny')
        raise
    finally:
        timer.deinit()
        digits[0].value(1)
        digits[1].value(1)
        for pin in segments:
            pin.value(1)


if __name__ == '__main__':
    main()
