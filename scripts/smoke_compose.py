"""Check actual HTTPS routing after Compose startup. Synthetic local deployment only."""
import json
import ssl
import time
import urllib.error
import urllib.request

# Caddy's local CA is not installed in the user's trust store by this script.
# This explicitly local smoke check disables TLS trust only for loopback localhost.
context = ssl._create_unverified_context()
# Caddy may start accepting TCP before its local certificate is ready.
for attempt in range(30):
    try:
        with urllib.request.urlopen('https://localhost:8443/health/ready', context=context, timeout=2) as response:
            assert json.load(response)['status'] == 'ready'
        break
    except (urllib.error.URLError, OSError):
        if attempt == 29:
            raise
        time.sleep(0.2)
for path, expected in [('/health/ready', 'status'), ('/api/v1/instance', 'display_name')]:
    with urllib.request.urlopen('https://localhost:8443' + path, context=context) as response:
        assert response.headers['Content-Type'].startswith('application/json')
        assert expected in json.load(response)
with urllib.request.urlopen('https://localhost:8443/', context=context) as response:
    assert 'text/html' in response.headers['Content-Type']
    assert 'Content-Security-Policy' in response.headers
print('Compose HTTPS API/static routing: PASS (local CA trust explicitly bypassed)')
