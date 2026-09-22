"""Test https:// URL validation on backend"""
import urllib.request, json

BASE = 'http://localhost:5000/api'

def post(path, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        BASE + path, data=data,
        headers={'Content-Type': 'application/json'}, method='POST'
    )
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

print("Testing URL validation...\n")

tests = [
    # (url, should_pass, label)
    ('https://example.com',          True,  'Valid https URL'),
    ('http://example.com',           True,  'http:// auto-upgraded to https://'),
    ('example.com',                  True,  'bare domain gets https:// prepended'),
    ('ftp://example.com',            False, 'ftp:// rejected'),
    ('javascript:alert(1)',          False, 'javascript: rejected'),
    ('https://youtube.com/watch?v=x', True, 'https with query string'),
    ('not-a-url-at-all!!!',          False, 'Gibberish string is rejected'),  # no valid domain
]

base_payload = {
    'sender_id': 1, 'receiver_id': 2,
    'message': 'test', 'message_type': 'link'
}

for url, should_pass, label in tests:
    payload = {**base_payload, 'file_url': url}
    data, status = post('/messages', payload)
    passed = (status == 201) == should_pass
    sym    = '✓' if passed else '✗'
    result = f"status={status}"
    if not passed:
        result += f"  expected={'pass' if should_pass else 'fail'}"
    print(f"  {sym}  {label:<40} {result}")

# Test shared-content validation
print("\nTesting shared-content URL validation...")
sc_tests = [
    ('https://github.com',     True,  'Valid https link'),
    ('http://github.com',      True,  'http auto-upgraded'),
    ('ftp://files.com',        False, 'ftp rejected'),
]
for url, should_pass, label in sc_tests:
    payload = {
        'sender_id': 1, 'receiver_id': 2,
        'title': 'Test', 'content_type': 'link',
        'media_type': 'website', 'file_url': url
    }
    data, status = post('/shared-content', payload)
    passed = (status == 201) == should_pass
    sym    = '✓' if passed else '✗'
    print(f"  {sym}  {label:<40} status={status}")
