#!/usr/bin/env python3
"""Cloudflare + GitHub Pages DNS setup for voting.uichain.org.
Credentials are passed via env vars (CF_EMAIL, CF_KEY) and never written to disk.
Steps: grey-cloud CNAME -> wait GitHub TLS cert -> ensure zone SSL=full -> orange cloud -> verify.
"""
import os, json, time, urllib.request, urllib.error, subprocess, sys

CF_EMAIL = os.environ.get('CF_EMAIL')
CF_KEY = os.environ.get('CF_KEY')
ZONE_NAME = 'uichain.org'
SUB = 'voting'
TARGET = 'leo-bone.github.io'
REPO = 'leo-bone/us-2026-midterms-dashboard'
GH = '/Users/leo/.workbuddy/binaries/gh/bin/gh'


def cf(method, path, data=None):
    url = 'https://api.cloudflare.com/client/v4' + path
    headers = {'X-Auth-Email': CF_EMAIL, 'X-Auth-Key': CF_KEY, 'Content-Type': 'application/json'}
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


def log(*a):
    print('[{}]'.format(time.strftime('%H:%M:%S')), *a, flush=True)


# 1. zone id
zr = cf('GET', '/zones?name=' + ZONE_NAME)
if not zr.get('success') or not zr.get('result'):
    log('FAIL get zone:', zr.get('errors')); sys.exit(1)
zone_id = zr['result'][0]['id']
log('zone_id', zone_id)

# 2. existing record
er = cf('GET', '/zones/{}/dns_records?name={}.{}'.format(zone_id, SUB, ZONE_NAME))
existing = er.get('result', [])
if existing:
    rid = existing[0]['id']
    log('update existing record', rid, 'was proxied=', existing[0].get('proxied'))
    ur = cf('PATCH', '/zones/{}/dns_records/{}'.format(zone_id, rid),
            {'content': TARGET, 'proxied': False, 'ttl': 1})
    log('update result', ur.get('success'), ur.get('errors'))
else:
    log('create CNAME', SUB + '.' + ZONE_NAME, '->', TARGET, '(grey cloud)')
    cr = cf('POST', '/zones/{}/dns_records'.format(zone_id),
            {'type': 'CNAME', 'name': SUB + '.' + ZONE_NAME, 'content': TARGET, 'proxied': False, 'ttl': 1})
    log('create result', cr.get('success'), cr.get('errors'))
    if not cr.get('success'):
        sys.exit(1)

# 3. poll GitHub cert (grey cloud phase)
log('waiting for GitHub Pages domain verification + TLS cert (grey cloud)...')
cert_active = False
for i in range(60):  # up to 30 min
    try:
        out = subprocess.run([GH, 'api', 'repos/{}/pages'.format(REPO)], capture_output=True, text=True, timeout=30)
        d = json.loads(out.stdout)
    except Exception as e:
        log('gh err', e); time.sleep(30); continue
    cert = (d.get('https_certificate') or {}).get('state')
    status = d.get('status')
    log('poll', i, 'status=', status, 'cert=', cert)
    if cert == 'active':
        cert_active = True
        break
    time.sleep(30)

if not cert_active:
    log('WARN: cert not active after polling; NOT switching to orange cloud. Manual check needed.')
    sys.exit(2)

# 4. ensure zone SSL = full (Cloudflare -> GitHub origin needs full, not flexible)
ssr = cf('GET', '/zones/{}/settings/ssl'.format(zone_id))
cur = ssr.get('result', {}).get('value')
log('current zone SSL:', cur)
if cur not in ('full', 'strict'):
    psr = cf('PATCH', '/zones/{}/settings/ssl'.format(zone_id), {'value': 'full'})
    log('set SSL=full:', psr.get('success'), psr.get('errors'))
else:
    log('zone SSL already', cur, '- OK')

# 5. switch to orange cloud
er = cf('GET', '/zones/{}/dns_records?name={}.{}'.format(zone_id, SUB, ZONE_NAME))
rid = er['result'][0]['id']
pr = cf('PATCH', '/zones/{}/dns_records/{}'.format(zone_id, rid), {'proxied': True})
log('orange cloud result', pr.get('success'), pr.get('errors'))

# 6. verify (retry, Cloudflare edge may take a few min)
log('verifying https://{}.{} ...'.format(SUB, ZONE_NAME))
ok = False
for i in range(20):
    try:
        v = subprocess.run(['curl', '-sI', 'https://{}.{}/'.format(SUB, ZONE_NAME)],
                           capture_output=True, text=True, timeout=20)
        head = v.stdout
        code = head.split('\n')[0] if head else '(no response)'
        log('verify', i, code)
        if '200' in code:
            ok = True
            log('FINAL: site reachable', code)
            break
    except Exception as e:
        log('curl err', e)
    time.sleep(20)
if not ok:
    log('WARN: verify not 200 yet; Cloudflare edge may need more time. Check later.')
log('DONE')
