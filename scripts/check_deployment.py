"""Unauthenticated HTTPS smoke checks; never seeds users or sends Telegram messages."""
import json
import sys
import urllib.error
import urllib.request

base = sys.argv[1].rstrip('/')
if not base.startswith('https://'):
    raise SystemExit('HTTPS is required; certificate validation remains enabled')


def request(path: str, data: bytes | None = None) -> tuple[int, object, bytes]:
    req = urllib.request.Request(base + path, data=data, headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read()


status, headers, body = request('/health/ready')
assert status == 200 and json.loads(body)['status'] == 'ready', 'readiness failed'
status, headers, body = request('/')
assert status == 200 and b'<html' in body.lower(), 'Mini App static failed'
assert headers['Cache-Control'] == 'no-store', 'cache protection missing'
assert 'https://web.telegram.org' in headers['Content-Security-Policy'], 'Telegram CSP missing'
status, headers, body = request('/r/deployment-invalid')
assert status == 200 and "frame-ancestors 'none'" in headers['Content-Security-Policy'], 'guest CSP missing'
for path in ('/.env', '/secrets/bot-token', '/secrets/keyring.json'):
    status, headers, body = request(path)
    assert status in (403, 404) or (status == 200 and 'text/html' in headers['Content-Type']), 'secret file exposed'
status, _, _ = request('/api/v1/sessions')
assert status == 401, 'sessions unexpectedly accessible'
status, _, _ = request('/api/v1/auth/telegram/miniapp', b'{"init_data":"invalid"}')
assert status == 401, 'invalid Telegram signature accepted'
status, _, _ = request('/api/v1/auth/telegram/miniapp', json.dumps({'init_data': 'x' * (600 * 1024)}).encode())
assert status == 413, 'normal body limit missing'
print('PASS: TLS, readiness, Mini App, guest CSP, secret-file denial, sessions, invalid Telegram, 512KiB cap')
