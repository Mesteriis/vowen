"""Conservative tracked-tree and history scan; never print matching secrets."""
import re
import subprocess
import sys

patterns = [
    rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    rb'gh[pousr]_[A-Za-z0-9]{30,}',
    rb'github_pat_[A-Za-z0-9_]{40,}',
    rb'\b\d{8,12}:[A-Za-z0-9_-]{35}\b',
]
paths = subprocess.check_output(['git', 'ls-files', '-z']).split(b'\0')
failed = False
for path in filter(None, paths):
    name = path.decode()
    if name.startswith('secrets/') or name == '.env' or name.endswith(('.jks', '.keystore')):
        print('Forbidden tracked path:', name)
        failed = True
    with open(name, 'rb') as stream:
        data = stream.read()
    if any(re.search(p, data) for p in patterns):
        print('Potential secret in:', name)
        failed = True
history = subprocess.run(['git', 'log', '-p', '--all'], capture_output=True, check=True).stdout
if any(re.search(p, history) for p in patterns):
    print('Potential secret in history')
    failed = True
print('Secret scan:', 'FAIL' if failed else 'PASS (heuristic; review still required)')
sys.exit(int(failed))
