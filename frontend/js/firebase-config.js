// ============================================================
//  Firebase Configuration
//  
//  WHERE TO FIND THESE VALUES:
//  Firebase Console → Your Project → ⚙️ Project Settings
//  → General tab → scroll to "Your apps" → your Web App
//  → "SDK setup and configuration" → Config
//
//  Copy each value from the firebaseConfig object shown there.
// ============================================================

// ⬇️ PASTE YOUR VALUES HERE (from Firebase Console)
const FIREBASE_CONFIG = {
    apiKey:            "YOUR_API_KEY",
    authDomain:        "YOUR_PROJECT_ID.firebaseapp.com",
    projectId:         "YOUR_PROJECT_ID",
    storageBucket:     "YOUR_PROJECT_ID.appspot.com",
    messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
    appId:             "YOUR_APP_ID"
};

// ── What each value means ────────────────────────────────────
// apiKey            → Web API Key  (visible in Project Settings → General)
// authDomain        → yourproject.firebaseapp.com
// projectId         → your project's unique ID
// storageBucket     → yourproject.appspot.com
// messagingSenderId → Cloud Messaging sender ID
// appId             → your web app's App ID

// ── Security note ────────────────────────────────────────────
// These values are safe to include in frontend code.
// Lock down which domains can use your key in:
//   Firebase Console → Authentication → Settings → Authorised domains
//   Add: localhost  (already added by default)

export { FIREBASE_CONFIG };
