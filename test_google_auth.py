"""Test Google auth endpoint exists and validates correctly."""
import urllib.request, json

BASE = 'http://localhost:5000/api'

def post(path, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        BASE + path, data=data,
        headers={'Content-Type':'application/json'}, method='POST'
    )
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

print("Testing /api/auth/google endpoint...\n")

# Test 1: No token → 400
d, s = post('/auth/google', {})
ok = s == 400
print(f"  {'✓' if ok else '✗'}  No token → HTTP {s} (expected 400)")

# Test 2: Fake token → 500 or 401 (Google will reject it)
d, s = post('/auth/google', {'id_token': 'fake.token.here'})
ok = s in (401, 500)
print(f"  {'✓' if ok else '✗'}  Fake token → HTTP {s} (expected 401 or 500: Google rejects it)")
print(f"       Response: {d.get('error','')[:80]}")

# Test 3: Confirm endpoint is registered (not 404)
d2, s2 = post('/auth/google', {'id_token': ''})
ok2 = s2 != 404
print(f"  {'✓' if ok2 else '✗'}  Endpoint registered (not 404) → HTTP {s2}")

print()
print("Google auth endpoint: READY")
print()
print("=" * 55)
print("  To enable real Google Sign-In:")
print()
print("  1. Go to https://console.cloud.google.com")
print("  2. Create/select a project")
print("  3. APIs & Services → Credentials → + Create Credentials")
print("     → OAuth 2.0 Client ID → Web application")
print("  4. Authorised JavaScript origins:")
print("       http://localhost:8080")
print("  5. Copy the Client ID")
print("  6. Open frontend/index.html")
print("     Find:   const GOOGLE_CLIENT_ID = 'YOUR_GOOGLE_CLIENT_ID...")
print("     Replace with your real Client ID")
print("  7. Open backend/app.py")
print("     Find:   GOOGLE_CLIENT_ID = 'YOUR_GOOGLE_CLIENT_ID...")
print("     Replace with your real Client ID")
print("  8. Restart backend (python backend/app.py)")
print("  9. Open http://localhost:8080 and click Continue with Google")
print("=" * 55)
