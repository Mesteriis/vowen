"""Loopback-only body-limit smoke. No auth bypass or real member is provisioned."""
import json
import ssl
import urllib.error
import urllib.request

# Same explicit local CA bypass as smoke_compose.py; never used by production clients.
context = ssl._create_unverified_context()
body = json.dumps({'idempotency_key': '00000000-0000-0000-0000-000000000001',
                   'kind': 'photo', 'media_type': 'image/png', 'data_base64': 'A' * 700000}).encode()
for path, wanted in [('/api/v1/ritual-occurrences/00000000-0000-0000-0000-000000000001/evidence',401),
                     ('/api/v1/auth/telegram',413)]:
    req = urllib.request.Request('https://localhost:8443'+path,data=body,headers={'Content-Type':'application/json'})
    try:
        urllib.request.urlopen(req,context=context,timeout=10)
    except urllib.error.HTTPError as error:
        assert error.code==wanted,(path,error.code,wanted)
    else:
        raise AssertionError('Unauthenticated request unexpectedly accepted')
print('Scoped HTTPS evidence body allowance + ordinary body limit: PASS')
