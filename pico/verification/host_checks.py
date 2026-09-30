"""Desktop logic checks with simulated hardware/HTTP, not a Pico integration test.
Run with CPython; optional uQR_reference.py is upstream JASchilz/uQR.
"""
import ast
import binascii
import calendar
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'main.py').read_text()
tree = ast.parse(source)
# Run actual firmware functions; replace only hardware/import/top-level IRQ setup.
nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.Assign))]

class Pin:
    OUT = 1
    def __init__(self, *args, **kwargs):
        pass

class OLED:
    def __init__(self):
        self.shown = 0
    def fill(self, *args): pass
    def text(self, *args): pass
    def fill_rect(self, *args): pass
    def show(self): self.shown += 1

fake_os = SimpleNamespace(listdir=os.listdir, urandom=os.urandom, sync=lambda: None,
                          rename=os.replace)
ns = dict(Pin=Pin, binascii=binascii, unique_id=lambda: b'host-test',
          hashlib=hashlib, os=fake_os, json=json, gc=gc,
          time=SimpleNamespace(time=time.time, gmtime=time.gmtime,
                               mktime=lambda t: calendar.timegm(t + (0,))))
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ROOT / 'main.py'), 'exec'), ns)

class Response:
    def __init__(self, payload, code=201):
        self.payload, self.status_code, self.closed = payload, code, False
    def json(self): return self.payload
    def close(self): self.closed = True

calls = []
responses = []
def post(url, **kwargs):
    calls.append((url, kwargs))
    response = responses.pop(0)
    if isinstance(response, Exception): raise response
    return response
ns['requests'] = SimpleNamespace(post=post)
ns['connect_wifi'] = lambda oled: None
ns['sync_clock'] = lambda: None
ns['qr_matrix'] = lambda url: [[False] * 57 for _ in range(57)]

def reply(pending, age=120, code=201):
    return Response({'acknowledged': True, 'token_id': 'test-token-id',
        'display_number': pending['payload']['display_number'],
        'reservation_expires_at': time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime(time.time()+age))}, code)

def must_raise(function, error):
    try: function()
    except error: return
    raise AssertionError('Expected ' + error.__name__)

previous = os.getcwd()
with tempfile.TemporaryDirectory() as directory:
    os.chdir(directory)
    try:
        state = ns['load_state']()
        assert state['next_numbers'] == [24]*4
        for i, service in enumerate(ns['SERVICES']):
            p = ns['build_pending'](state, i)
            parsed = urlsplit(p['url'])
            query, fragment = parse_qs(parsed.query), parse_qs(parsed.fragment)
            assert 'preview' not in query
            assert query['cat'][0] == service[2]
            assert query['reservation'][0] == p['payload']['hardware_reservation_id']
            assert ns['digest'](fragment['claim'][0]) == p['payload']['claim_secret_hash']
            assert len(fragment['claim'][0]) == 32
            assert p['payload']['service_id'] == service[4]
        print('PASS: all four QR categories, service IDs and claim hashes')

        # Simulate a lost response after POST. Persistent identity must exist already.
        responses.append(OSError('simulated lost response'))
        must_raise(lambda: ns['issue_or_recover'](OLED(), state, 0), OSError)
        recovered = ns['load_state']()
        assert recovered['pending'] == state['pending']
        assert recovered['next_numbers'] == [25,24,24,24]
        first_request = calls[-1]
        response = reply(recovered['pending'])
        responses.append(response)
        assert ns['issue_or_recover'](OLED(), recovered, 3) == 15000
        assert calls[-1] == first_request  # Different button cannot change pending identity.
        assert response.closed
        assert ns['load_state']()['pending'] == recovered['pending']
        ns['clear_pending'](recovered)
        assert ns['load_state']()['next_numbers'] == [25,24,24,24]
        assert ns['load_state']()['pending'] is None
        print('PASS: lost-response/reboot retry preserves payload, IDs and number')

        # A prior success may be expired by the time idempotency recovers it.
        recovered['pending'] = ns['build_pending'](recovered, 1)
        recovered['next_numbers'][1] += 1
        ns['save_state'](recovered)
        responses.append(reply(recovered['pending'], age=-10))
        shown = []
        real_show_qr = ns['show_qr']
        ns['show_qr'] = lambda *a: shown.append(True)
        assert ns['issue_or_recover'](OLED(), recovered, 1) is None
        assert not shown and ns['load_state']()['pending'] is None
        print('PASS: expired acknowledgements cannot display a QR')

        recovered['pending'] = ns['build_pending'](recovered, 2)
        ns['save_state'](recovered)
        bad = reply(recovered['pending'], code=401)
        responses.append(bad)
        must_raise(lambda: ns['issue_or_recover'](OLED(), recovered, 2), OSError)
        assert bad.closed and not shown and ns['load_state']()['pending']
        bad = reply(recovered['pending'])
        bad.payload['display_number'] = 'WRONG'
        responses.append(bad)
        must_raise(lambda: ns['reserve'](recovered['pending']), ValueError)
        assert bad.closed
        print('PASS: HTTP errors/mismatched acknowledgements retain request, no QR')

        # Failed persistent commit must prevent HTTP submission.
        ns['clear_pending'](recovered)
        save = ns['save_state']
        def broken_save(state): raise OSError('disk full')
        ns['save_state'] = broken_save
        count = len(calls)
        must_raise(lambda: ns['issue_or_recover'](OLED(), recovered, 0), OSError)
        assert len(calls) == count
        ns['save_state'] = save
        assert ns['load_state']()['pending'] is None
        print('PASS: disk failure before reservation prevents POST')

        Path(ns['STATE_FILE']).write_text('{"corrupted":true}')
        must_raise(ns['load_state'], RuntimeError)
        print('PASS: corrupt state fails closed instead of resetting numbers')
    finally:
        os.chdir(previous)

# Exercise the actual display synchronization with simulated HTTP/Wi-Fi.
ns['network'] = SimpleNamespace(STA_IF=0, WLAN=lambda _: SimpleNamespace(
    active=lambda _: None, isconnected=lambda: True))
def get_display(url, **kwargs):
    assert url.endswith('/hardware/counters/ctr-02/display')
    assert kwargs['headers']['X-Hardware-Secret'] == ns['HARDWARE_SECRET']
    assert kwargs['timeout'] == 3
    response = responses.pop(0)
    if isinstance(response, Exception): raise response
    return response
ns['requests'].get = get_display
for token, status in [('B024', 'CALLED'), ('B034', 'SERVING'), (None, None), ('B100', 'CALLED')]:
    response = Response({'counter_id': 'ctr-02', 'display_number': token, 'token_status': status}, 200)
    responses.append(response)
    ns['sync_serving']()
    expected = ((ns['BLANK'], ns['BLANK']) if token is None else
                (ns['DASH'], ns['DASH']) if token == 'B100' else
                (ns['PATTERNS'][int(token[1:]) // 10], ns['PATTERNS'][int(token[1:]) % 10]))
    assert ns['display_frame'] == expected
    assert response.closed
for response in [Response({}, 401), Response({'counter_id': 'wrong'}, 200), OSError('timeout')]:
    ns['set_serving']('B024')
    responses.append(response)
    must_raise(ns['sync_serving'], (OSError, ValueError))
    assert ns['display_frame'] == (ns['BLANK'], ns['BLANK'])
    if isinstance(response, Response): assert response.closed
ns['handle_command']('SERVE B024')
assert ns['display_auto'] is False
ns['handle_command']('AUTO')
assert ns['display_auto'] is True
print('PASS: counter display sync, blank/overflow, error clearing, response cleanup and manual/AUTO modes')

# Check the real upstream uQR matrix, without running on a Pico.
reference = Path(__file__).with_name('uQR_reference.py')
if reference.exists():
    sys.modules['ure'] = re
    spec = importlib.util.spec_from_file_location('uQR_reference', reference)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for i, service in enumerate(ns['SERVICES']):
        pending = ns['build_pending']({'next_numbers': [24]*4}, i)
        qr = module.QRCode()
        qr.add_data(pending['url'])
        size = len(qr.get_matrix())
        assert size <= 64, (service[2], size)
        print('PASS: upstream uQR', service[2], len(pending['url']), 'URL bytes;', size, 'pixels including quiet zone')
else:
    print('UNVERIFIED: upstream uQR matrix size (reference library unavailable)')
