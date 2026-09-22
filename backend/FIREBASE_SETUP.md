# Firebase Setup for SkillX Backend

## Step 1 — Get your Firebase config values (for frontend)

1. Go to https://console.firebase.google.com
2. Select your project
3. Click ⚙️ **Project Settings** → **General** tab
4. Scroll to **"Your apps"** → click your Web App `</>`
5. Under "SDK setup and configuration" choose **Config**
6. You'll see:

```js
const firebaseConfig = {
  apiKey:            "AIza...",        ← copy this
  authDomain:        "project.firebaseapp.com",  ← copy this
  projectId:         "your-project-id",          ← copy this
  storageBucket:     "your-project.appspot.com", ← copy this
  messagingSenderId: "123456789",                ← copy this
  appId:             "1:123:web:abc..."           ← copy this
};
```

7. Open `frontend/index.html`
8. Find `const firebaseConfig = {` (search for `YOUR_API_KEY`)
9. Replace each value with what you copied

---

## Step 2 — Get service account key (for backend — optional but recommended)

This enables cryptographic token verification (most secure).
Without it, the backend uses Google's tokeninfo API (also secure, just slower).

1. Firebase Console → ⚙️ Project Settings → **Service accounts** tab
2. Click **"Generate new private key"**
3. Save the downloaded JSON file as:
   `backend/firebase-service-account.json`
4. Restart the backend — it will print:
   `✓ Firebase Admin SDK initialised from service account key`

**⚠️ NEVER commit this file to git.**
It is already in `.gitignore`.

---

## Step 3 — Add localhost to Authorised domains

1. Firebase Console → **Authentication** → **Settings** tab
2. Under "Authorised domains" click **Add domain**
3. Add: `localhost`
4. (It may already be there by default)

---

## Summary of what you need

| Where | What to paste |
|-------|---------------|
| `frontend/index.html` → `firebaseConfig` | All 6 config values from Project Settings |
| `backend/firebase-service-account.json` | Downloaded JSON key file (optional but recommended) |

That's it — no Google Cloud Console needed.
